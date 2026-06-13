# ruff: noqa: E501

import re
import threading
import time
from typing import Any

from corporate_rag.graph.interfaces import BaseGraphReader


class TypeaheadCache:
    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl_seconds = ttl_seconds
        self.lock = threading.Lock()
        self.data: dict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = {}

    def get(self, key: tuple[str, int]) -> list[dict[str, Any]] | None:
        with self.lock:
            entry = self.data.get(key)
            if entry is None:
                return None

            stored_at, value = entry
            if time.time() - stored_at > self.ttl_seconds:
                del self.data[key]
                return None

            return [dict(item) for item in value]

    def set(self, key: tuple[str, int], value: list[dict[str, Any]]) -> None:
        with self.lock:
            self.data[key] = (time.time(), [dict(item) for item in value])

    def invalidate(self) -> None:
        with self.lock:
            self.data.clear()


def run_typeahead(
    client: BaseGraphReader,
    *,
    kind: str,
    query_text: str,
    limit: int,
    context: dict[str, str] | None = None,
    cache: TypeaheadCache | None = None,
) -> tuple[list[dict[str, Any]], float, bool]:
    validate_typeahead_kind(kind)
    bounded_limit = max(1, min(limit, TYPEAHEAD_BROWSE_CAP))
    is_browse = not query_text
    has_context = bool(context)
    effective_limit = TYPEAHEAD_BROWSE_CAP if is_browse else bounded_limit
    cache_key = (kind, -1 if is_browse else bounded_limit)
    use_cache = is_browse and not has_context and cache is not None

    if use_cache and cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached[:bounded_limit], 0.0, True

    cypher = typeahead_cypher_for_kind(kind, has_query=bool(query_text), context=context)
    parameters = typeahead_parameters(kind, query_text, effective_limit, context=context)

    started_at = time.perf_counter()
    rows = client.read(cypher, parameters)
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0

    payload = hydrate_typeahead_rows(rows, include_score=bool(query_text))
    if use_cache and cache is not None and payload:
        cache.set(cache_key, payload)

    return payload[:bounded_limit], elapsed_ms, False


def validate_typeahead_kind(kind: str) -> None:
    if kind not in TYPEAHEAD_KINDS:
        allowed = ", ".join(sorted(TYPEAHEAD_KINDS))
        raise ValueError(f"Unknown typeahead kind {kind!r}; expected one of: {allowed}")


def context_from_query(parameters: dict[str, str | None]) -> dict[str, str]:
    context: dict[str, str] = {}
    for key in TYPEAHEAD_CONTEXT_KEYS:
        value = parameters.get(key)
        if value:
            context[key] = value
    return context


def typeahead_parameters(
    kind: str,
    query_text: str,
    limit: int,
    context: dict[str, str] | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {"limit": limit}
    for key, value in (context or {}).items():
        parameters[f"context_{key}"] = value

    if not query_text:
        return parameters

    if kind in {"file", "module"}:
        parameters["contains"] = query_text
        return parameters

    cleaned = re.sub(r"[^\w\s]", " ", query_text).strip()
    tokens = cleaned.split()
    parameters["lucene"] = " ".join(f"{token}*" for token in tokens) if tokens else "*"
    parameters["query_lower"] = " ".join(tokens).lower()
    parameters["query_compact"] = "".join(tokens).lower()
    parameters["query_tokens"] = [token.lower() for token in tokens]
    return parameters


def hydrate_typeahead_rows(
    rows: list[dict[str, Any]],
    *,
    include_score: bool,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        identifier = row.get("id")
        label = row.get("label")
        if identifier is None or label is None:
            continue
        key = (str(identifier), str(label).strip().casefold())
        if key in seen:
            continue
        seen.add(key)

        item: dict[str, Any] = {
            "id": str(identifier),
            "label": str(label),
            "hint": row.get("hint"),
            "edge_count": int(row.get("edge_count") or 0),
        }
        aliases = row.get("aliases")
        if aliases is not None:
            item["aliases"] = aliases
        if include_score:
            item["score"] = float(row.get("score") or 0.0)
        payload.append(item)

    return payload


COMPANY_LABEL = "LegalEntity"
TYPEAHEAD_KINDS: frozenset[str] = frozenset(
    {
        "subject",
        "person",
        "phase",
        "event",
        "work",
        "file",
        "organization",
        "class",
        "module",
    }
)


def typeahead_cypher_for_kind(
    kind: str,
    *,
    has_query: bool,
    context: dict[str, str] | None = None,
) -> str:
    context_filter = context_clause_for_kind(kind, context or {})

    def context_block() -> str:
        if not context_filter:
            return ""
        return f"WITH n, score\nWHERE {context_filter}\n"

    if kind == "subject":
        seed = (
            "CALL db.index.fulltext.queryNodes('subject_search', $lucene)\n"
            "YIELD node AS n, score\n"
            if has_query
            else seed_with_default_score("MATCH (n:BusinessSubject)\n")
        )
        return seed + context_block() + """
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.label ASC
LIMIT toInteger($limit)
RETURN n.subjectId AS id,
       n.label AS label,
       'family root' AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    if kind == "person":
        seed = (
            "CALL db.index.fulltext.queryNodes('entity_search', $lucene)\n"
            "YIELD node AS n, score\n"
            "WHERE n:Person\n"
            if has_query
            else seed_with_default_score("MATCH (n:Entity:Person)\n")
        )
        return seed + context_block() + """
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.label ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (b)-[:HAS_PARTY_IN_CONTROL]->(n)
WHERE b:BoardMembership OR b:Employment OR b:MeetingFunction OR b:Affiliation
OPTIONAL MATCH (b)-[:INVOLVES_CONTROLLED_THING]->(org)
OPTIONAL MATCH (b)-[:HAS_PARTY_ROLE]->(pr:PartyRole)
WITH n, score, edge_count,
     head(collect(DISTINCT org.label)) AS org_hint,
     head(collect(DISTINCT pr.label)) AS role_hint
RETURN n.entityId AS id,
       n.label AS label,
       n.aliases AS aliases,
       coalesce(org_hint, role_hint) AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    if kind == "phase":
        seed = (
            "CALL db.index.fulltext.queryNodes('entity_search', $lucene)\n"
            "YIELD node AS n, score\n"
            "WHERE EXISTS { MATCH (:BusinessSubject)-[:HAS_PHASE]->(n) }\n"
            if has_query
            else seed_with_default_score("MATCH (:BusinessSubject)-[:HAS_PHASE]->(n)\n")
        )
        return seed + context_block() + """
WITH DISTINCT n, score
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.label ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (s:BusinessSubject)-[:HAS_PHASE]->(n)
WITH n, score, edge_count, head(collect(s.label)) AS hint
RETURN n.entityId AS id,
       n.label AS label,
       hint AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    if kind == "event":
        seed = (
            "CALL db.index.fulltext.queryNodes('entity_search', $lucene)\n"
            "YIELD node AS n, score\n"
            "WHERE n:Event\n"
            if has_query
            else seed_with_default_score("MATCH (n:Entity:Event)\n")
        )
        return seed + context_block() + """
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.label ASC
LIMIT toInteger($limit)
RETURN n.entityId AS id,
       n.label AS label,
       trim(coalesce(n.eventType, '') + ' ' + coalesce(n.effectiveDate, '')) AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    if kind == "work":
        seed = (
            "CALL db.index.fulltext.queryNodes('work_search', $lucene)\n"
            "YIELD node AS n, score\n"
            "WHERE n.work_id IS NOT NULL AND n.title IS NOT NULL\n"
            if has_query
            else seed_with_default_score(
                "MATCH (n:Work) WHERE n.work_id IS NOT NULL AND n.title IS NOT NULL\n"
            )
        )
        return seed + context_block() + """
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.title ASC
LIMIT toInteger($limit)
RETURN n.work_id AS id,
       n.title AS label,
       n.doc_type AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    if kind == "organization":
        seed = (
            "CALL db.index.fulltext.queryNodes('entity_search', $lucene)\n"
            "YIELD node AS n, score\n"
            f"WHERE n:{COMPANY_LABEL}\n"
            if has_query
            else seed_with_default_score(f"MATCH (n:Entity:{COMPANY_LABEL})\n")
        )
        return seed + context_block() + organization_return_block(has_query)

    if kind == "file":
        seed = (
            seed_with_default_score(
                "MATCH (n:Item)\n"
                "WHERE n.inbox_filename IS NOT NULL\n"
                "  AND toLower(n.inbox_filename) CONTAINS toLower($contains)\n"
            )
            if has_query
            else seed_with_default_score("MATCH (n:Item) WHERE n.inbox_filename IS NOT NULL\n")
        )
        return seed + context_block() + """
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.inbox_filename ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (n)<-[:HAS_EXEMPLAR]-(:Manifestation)<-[:HAS_EMBODIMENT]-(:Expression)<-[:HAS_REALIZATION]-(w:Work)
WITH n, score, edge_count, head(collect(w.doc_type)) AS hint
RETURN coalesce(n.item_id, n.inbox_filename) AS id,
       n.inbox_filename AS label,
       hint AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    if kind == "class":
        seed = (
            "CALL db.index.fulltext.queryNodes('class_search', $lucene)\n"
            "YIELD node AS n, score\n"
            "WHERE n:Class\n"
            if has_query
            else seed_with_default_score("MATCH (n:Class)\n")
        )
        return seed + context_block() + class_return_block(has_query)

    if kind == "module":
        seed = (
            seed_with_default_score(
                "MATCH (n:Module)\n"
                "WHERE toLower(n.localName) CONTAINS toLower($contains)\n"
                "   OR toLower(coalesce(n.parent, '')) CONTAINS toLower($contains)\n"
            )
            if has_query
            else seed_with_default_score("MATCH (n:Module)\n")
        )
        return seed + context_block() + """
WITH n, score, COUNT { (:Class)-[:DEFINED_IN]->(n) } AS edge_count
ORDER BY edge_count DESC, n.localName ASC
LIMIT toInteger($limit)
RETURN n.localName AS id,
       n.localName AS label,
       coalesce(n.parent, '') AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    raise ValueError(f"unknown typeahead kind: {kind!r}")


def context_clause_for_kind(kind: str, context: dict[str, str]) -> str:
    if "subject_id" not in context or kind == "subject":
        return ""

    if kind == "phase":
        return (
            "EXISTS { MATCH (:BusinessSubject {subjectId: $context_subject_id})"
            "-[:HAS_PHASE]->(n) }"
        )

    if kind == "person":
        return (
            "EXISTS { MATCH (:BusinessSubject {subjectId: $context_subject_id})"
            "-[:HAS_PHASE]->(phase:Entity) WHERE phase <> n "
            "MATCH (n)--(mid:Entity)--(phase) }"
        )

    if kind == "organization":
        return (
            "(EXISTS { MATCH (:BusinessSubject {subjectId: $context_subject_id})"
            "-[:HAS_PHASE]->(n) } "
            "OR EXISTS { MATCH (:BusinessSubject {subjectId: $context_subject_id})"
            "-[:HAS_PHASE]->(phase:Entity) WHERE phase <> n "
            "MATCH (n)--(mid:Entity)--(phase) WHERE mid <> n AND mid <> phase })"
        )

    if kind == "event":
        return (
            "EXISTS { MATCH (:BusinessSubject {subjectId: $context_subject_id})"
            "-[:HAS_PHASE]->(phase:Entity) MATCH (n)-[]-(phase) }"
        )

    return ""


def seed_with_default_score(match_clause: str) -> str:
    return f"{match_clause}WITH n, 0.0 AS score\n"


def organization_return_block(has_query: bool) -> str:
    if not has_query:
        return """
WITH DISTINCT n, score
WITH n, score, COUNT { (n)--() } AS edge_count
ORDER BY edge_count DESC, n.label ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (n)-[:INSTANCE_OF]->(class:Class)
RETURN n.entityId AS id,
       n.label AS label,
       class.localName AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    return """
WITH DISTINCT n, score
WITH n, score, COUNT { (n)--() } AS edge_count
WITH n, score, edge_count,
     CASE
       WHEN $query_lower <> '' AND toLower(coalesce(n.label, '')) = $query_lower THEN 6
       WHEN $query_compact <> '' AND replace(toLower(coalesce(n.label, '')), ' ', '') = $query_compact THEN 6
       WHEN $query_lower <> '' AND toLower(coalesce(n.label, '')) STARTS WITH $query_lower THEN 5
       WHEN $query_compact <> '' AND replace(toLower(coalesce(n.label, '')), ' ', '') STARTS WITH $query_compact THEN 5
       WHEN $query_lower <> '' AND toLower(coalesce(n.label, '')) CONTAINS $query_lower THEN 4
       WHEN $query_compact <> '' AND replace(toLower(coalesce(n.label, '')), ' ', '') CONTAINS $query_compact THEN 4
       WHEN all(token IN $query_tokens WHERE toLower(coalesce(n.label, '')) CONTAINS token) THEN 3
       WHEN any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) = $query_lower) THEN 3
       WHEN any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS $query_lower) THEN 2
       ELSE 0
     END AS textual_rank
ORDER BY textual_rank DESC, score DESC, edge_count DESC, n.label ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (n)-[:INSTANCE_OF]->(class:Class)
RETURN n.entityId AS id,
       n.label AS label,
       class.localName AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()


def class_return_block(has_query: bool) -> str:
    if not has_query:
        return """
WITH n, score, COUNT { (n)-[:HAS_SUBCLASS]->(:Class) } AS edge_count
ORDER BY edge_count DESC, n.localName ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (n)-[:DEFINED_IN]->(m:Module)
RETURN n.localName AS id,
       coalesce(n.label, n.localName) AS label,
       coalesce(n.module, m.localName) AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()

    return """
WITH n, score, COUNT { (n)-[:HAS_SUBCLASS]->(:Class) } AS edge_count
WITH n, score, edge_count,
     CASE
       WHEN $query_compact <> '' AND toLower(n.localName) = $query_compact THEN 4
       WHEN $query_lower <> '' AND toLower(coalesce(n.label, '')) = $query_lower THEN 4
       WHEN $query_compact <> '' AND replace(toLower(coalesce(n.label, '')), ' ', '') = $query_compact THEN 4
       WHEN $query_compact <> '' AND toLower(n.localName) STARTS WITH $query_compact THEN 3
       WHEN $query_lower <> '' AND toLower(coalesce(n.label, '')) STARTS WITH $query_lower THEN 3
       WHEN $query_compact <> '' AND replace(toLower(coalesce(n.label, '')), ' ', '') STARTS WITH $query_compact THEN 3
       WHEN $query_compact <> '' AND toLower(n.localName) CONTAINS $query_compact THEN 2
       WHEN $query_lower <> '' AND toLower(coalesce(n.label, '')) CONTAINS $query_lower THEN 2
       WHEN $query_compact <> '' AND replace(toLower(coalesce(n.label, '')), ' ', '') CONTAINS $query_compact THEN 2
       ELSE 0
     END AS textual_rank
ORDER BY textual_rank DESC, score DESC, edge_count DESC, n.localName ASC
LIMIT toInteger($limit)
OPTIONAL MATCH (n)-[:DEFINED_IN]->(m:Module)
RETURN n.localName AS id,
       coalesce(n.label, n.localName) AS label,
       coalesce(n.module, m.localName) AS hint,
       edge_count AS edge_count,
       score AS score
""".strip()



TYPEAHEAD_BROWSE_CAP = 10000
TYPEAHEAD_CONTEXT_KEYS: frozenset[str] = frozenset({"subject_id"})
