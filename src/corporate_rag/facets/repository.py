from dataclasses import dataclass
from typing import Any

from corporate_rag.graph.interfaces import BaseGraphReader


def resolve_facet(
    client: BaseGraphReader,
    *,
    workflow_id: str,
    parameter_name: str,
    current_parameters: dict[str, Any],
) -> list[dict[str, Any]]:
    facet = get_facet(workflow_id, parameter_name)
    parameters = build_facet_parameters(facet, current_parameters)
    rows = client.read(facet.cypher, parameters)
    return [
        {"value": row.get("value"), "count": int(row.get("count") or 0)}
        for row in rows
        if row.get("value") is not None
    ]


def facetable_pairs() -> list[tuple[str, str]]:
    return sorted(FACETS.keys())


def get_facet(workflow_id: str, parameter_name: str) -> "FacetQuery":
    key = (workflow_id, parameter_name)
    if key not in FACETS:
        raise KeyError(f"Unknown facet: {workflow_id}.{parameter_name}")
    return FACETS[key]


def build_facet_parameters(
    facet: "FacetQuery",
    current_parameters: dict[str, Any],
) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for name in facet.parameters:
        value = current_parameters.get(name)
        if name == "include_cancelled":
            parameters[name] = coerce_bool(value)
        else:
            parameters[name] = value if value != "" else None
    return parameters


def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


@dataclass(frozen=True)
class FacetQuery:
    cypher: str
    parameters: tuple[str, ...]
    requires: tuple[str, ...] = ()


DOCUMENT_DOC_TYPE_FACET = FacetQuery(
    cypher="""
WITH coalesce($signatory_person_id, '') AS signatory_id,
     coalesce($subject_id, '') AS subject_id,
     coalesce($text_query, '') AS text_query,
     coalesce($file, '') AS file_id
WITH signatory_id, subject_id, text_query, file_id,
     signatory_id <> '' AS has_signatory,
     subject_id <> '' AS has_subject,
     text_query <> '' AS has_text,
     file_id <> '' AS has_file
MATCH (w:Work)-[:HAS_REALIZATION]->(expr:Expression)
MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
OPTIONAL MATCH (expr)-[:HAS_EFFECTIVE_DATE]->(d:Entity:Date)
WITH w, expr, item,
     signatory_id, subject_id, text_query, file_id,
     has_signatory, has_subject, has_text, has_file,
     toString(d.iso_date) AS effective_date
WHERE
  ($since IS NULL OR effective_date >= $since)
  AND ($until IS NULL OR effective_date <= $until)
  AND (NOT has_file OR item.item_id = file_id OR item.inbox_filename = file_id)
  AND (NOT has_signatory OR EXISTS {
    MATCH (expr)-[:DESIGNATES_SIGNATORY]->(p:Entity {entityId: signatory_id})
  })
  AND (NOT has_subject OR EXISTS {
    MATCH (s:BusinessSubject {subjectId: subject_id})-[:HAS_PHASE]->(phase:Entity)
    MATCH (expr)-[:MENTIONS|RECORDS|DESIGNATES_SIGNATORY|EVIDENCES]->(phase)
  })
  AND (
    NOT has_text
    OR toLower(coalesce(w.title, '')) CONTAINS toLower(text_query)
    OR toLower(coalesce(w.summary, '')) CONTAINS toLower(text_query)
    OR toLower(coalesce(w.doc_type, '')) CONTAINS toLower(text_query)
  )
  AND (
    $include_cancelled
    OR (
      coalesce(w.lifecycle_status, 'active') = 'active'
      AND coalesce(expr.lifecycle_status, 'active') = 'active'
      AND coalesce(item.lifecycle_status, 'active') = 'active'
    )
  )
WITH DISTINCT w
WITH w.doc_type AS value, count(*) AS count
WHERE value IS NOT NULL
RETURN value, count
ORDER BY count DESC
""".strip(),
    parameters=(
        "signatory_person_id",
        "subject_id",
        "text_query",
        "file",
        "since",
        "until",
        "include_cancelled",
    ),
)

EVENT_TYPE_FACET = FacetQuery(
    cypher="""
MATCH (e:Entity:Event)
OPTIONAL MATCH (e)-[:HAS_EFFECTIVE_DATE]->(d:Entity:Date)
WITH e, coalesce(toString(d.iso_date), e.effectiveDate) AS effective_date
WHERE
  ($since IS NULL OR effective_date >= $since)
  AND ($until IS NULL OR effective_date <= $until)
  AND (
    $q IS NULL OR $q = ''
    OR toLower(coalesce(e.label, '')) CONTAINS toLower($q)
    OR toLower(coalesce(e.eventType, '')) CONTAINS toLower($q)
  )
  AND (
    $subject_id IS NULL OR $subject_id = ''
    OR EXISTS {
      MATCH (s:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
      MATCH (e)-[r]->(phase)
      WHERE type(r) IN ['HAS_ACTOR', 'HAS_UNDERGOER', 'HAS_COUNTERPARTY',
                        'INVOLVES_CONTROLLED_THING', 'RELATED_ENDEAVOUR']
        AND (
          effective_date IS NULL
          OR (
            (phase.phase_valid_from IS NULL OR effective_date >= phase.phase_valid_from)
            AND effective_date <= coalesce(phase.phase_valid_to, toString(date()))
          )
        )
    }
  )
  AND (
    $participant_id IS NULL OR $participant_id = ''
    OR EXISTS {
      MATCH (e)-[:HAS_ACTOR|HAS_UNDERGOER]->(:Entity:LegalEntity {entityId: $participant_id})
    }
  )
  AND (
    $file IS NULL OR $file = ''
    OR EXISTS {
      MATCH (file_expr:Expression)-[:MENTIONS|RECORDS|EVIDENCES]->(e)
      MATCH (file_expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(file_item:Item)
      WHERE file_item.item_id = $file OR file_item.inbox_filename = $file
    }
    OR EXISTS {
      MATCH (file_chunk:Chunk)-[:EVIDENCES]->(e)
      MATCH (file_chunk)<-[:HAS_PART]-(file_expr2:Expression)
      MATCH (file_expr2)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(file_item2:Item)
      WHERE file_item2.item_id = $file OR file_item2.inbox_filename = $file
    }
  )
OPTIONAL MATCH (src:Expression)-[:RECORDS|MENTIONS]->(e)
OPTIONAL MATCH (src)<-[:HAS_REALIZATION]-(w:Work)
OPTIONAL MATCH (src)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WITH e, src, w, item
WHERE
  $include_cancelled
  OR src IS NULL
  OR (
    coalesce(w.lifecycle_status, 'active') = 'active'
    AND coalesce(src.lifecycle_status, 'active') = 'active'
    AND coalesce(item.lifecycle_status, 'active') = 'active'
  )
WITH DISTINCT e
WITH e.eventType AS value, count(*) AS count
WHERE value IS NOT NULL
RETURN value, count
ORDER BY count DESC
""".strip(),
    parameters=(
        "subject_id",
        "participant_id",
        "file",
        "q",
        "since",
        "until",
        "include_cancelled",
    ),
)

FACETS: dict[tuple[str, str], FacetQuery] = {
    ("documents.search", "doc_type"): DOCUMENT_DOC_TYPE_FACET,
    ("events.timeline", "event_type"): EVENT_TYPE_FACET,
}
