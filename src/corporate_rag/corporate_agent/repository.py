from typing import Any

from corporate_rag.documents.repository import fetch_document_source
from corporate_rag.graph.interfaces import BaseGraphReader

GET_WORK_CYPHER = """
MATCH (w:Work {work_id: $work_id})
OPTIONAL MATCH (w)-[:HAS_REALIZATION]->(expr:Expression)
OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
OPTIONAL MATCH (expr)-[:HAS_PART]->(chunk:Chunk)
WITH w, expr, item, count(DISTINCT chunk) AS chunk_count
RETURN w.work_id AS work_id,
       w.title AS title,
       w.doc_type AS doc_type,
       w.summary AS summary,
       item.inbox_filename AS file,
       chunk_count
""".strip()

READ_CHUNKS_BY_ID_CYPHER = """
MATCH (chunk:Chunk)
WHERE chunk.chunk_id IN $chunk_ids
MATCH (expr:Expression)-[:HAS_PART]->(chunk)
MATCH (expr)<-[:HAS_REALIZATION]-(work:Work)
OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
RETURN work.work_id AS work_id,
       work.title AS work_title,
       item.inbox_filename AS file,
       chunk.chunk_id AS chunk_id,
       chunk.sequence_index AS sequence_index,
       chunk.page_first AS page_first,
       chunk.page_last AS page_last,
       chunk.text AS text
ORDER BY sequence_index ASC
LIMIT toInteger($limit)
""".strip()

ENTITY_MENTIONS_CYPHER = """
CALL {
  MATCH (chunk:Chunk)-[r:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->
        (:Entity {entityId: $entity_id})
  MATCH (expr:Expression)-[:HAS_PART]->(chunk)
  RETURN chunk, expr, type(r) AS relation_type, 0 AS source_rank
  UNION
  MATCH (expr:Expression)-[r:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->
        (:Entity {entityId: $entity_id})
  MATCH (expr)-[:HAS_PART]->(chunk:Chunk)
  RETURN chunk, expr, type(r) AS relation_type, 1 AS source_rank
}
MATCH (expr)<-[:HAS_REALIZATION]-(w:Work)
OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WITH chunk, w, item, relation_type, source_rank
ORDER BY source_rank ASC
WITH chunk.chunk_id AS chunk_id,
     relation_type,
     head(collect({
       work_id: w.work_id,
       work_title: w.title,
       doc_type: w.doc_type,
       file: item.inbox_filename,
       chunk_id: chunk.chunk_id,
       sequence_index: chunk.sequence_index,
       page_first: chunk.page_first,
       page_last: chunk.page_last,
       text: chunk.text,
       relation_type: relation_type
     })) AS best_row
RETURN best_row.work_id AS work_id,
       best_row.work_title AS work_title,
       best_row.doc_type AS doc_type,
       best_row.file AS file,
       best_row.chunk_id AS chunk_id,
       best_row.sequence_index AS sequence_index,
       best_row.page_first AS page_first,
       best_row.page_last AS page_last,
       best_row.text AS text,
       best_row.relation_type AS relation_type
ORDER BY sequence_index ASC
LIMIT toInteger($limit)
""".strip()

FIND_BY_IDENTIFIER_CYPHER = """
MATCH (identifier:Entity)-[:INSTANCE_OF]->(identifier_class:Class)
WHERE identifier_class.localName ENDS WITH 'Identifier'
  AND ($kind IS NULL OR $kind = '' OR identifier_class.localName = $kind)
WITH identifier, identifier_class,
     coalesce(identifier.identifierValue, identifier.label) AS identifier_value
WHERE identifier_value = $value
   OR ($allow_prefix AND identifier_value STARTS WITH $value)
MATCH (owner)-[:IS_IDENTIFIED_BY|HAS_IDENTIFIER|IS_REGISTERED_BY]->(identifier)
RETURN CASE
         WHEN owner:BusinessSubject THEN owner.subjectId
         ELSE owner.entityId
       END AS owner_id,
       CASE
         WHEN owner:BusinessSubject THEN 'BusinessSubject'
         ELSE 'Entity'
       END AS owner_kind,
       owner.label AS label,
       identifier_class.localName AS identifier_kind,
       identifier_value AS identifier_value
ORDER BY label ASC
""".strip()

SEARCH_DOCUMENTS_FULLTEXT_CYPHER = """
CALL db.index.fulltext.queryNodes('work_search', $query) YIELD node, score
MATCH (node)-[:HAS_REALIZATION]->(expr:Expression)
OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
OPTIONAL MATCH (expr)-[:HAS_EFFECTIVE_DATE]->(d:Entity:Date)
WITH node, expr, item,
     coalesce(d.date, d.value, node.effectiveDate, node.document_date) AS effective_date,
     score
WHERE ($doc_type IS NULL OR $doc_type = '' OR node.doc_type = $doc_type)
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {
    MATCH (:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
    WHERE (expr)-[:MENTIONS|RECORDS|EVIDENCES|DESIGNATES_SIGNATORY]->(phase)
       OR EXISTS {
         MATCH (expr)-[:MENTIONS|RECORDS|EVIDENCES|DESIGNATES_SIGNATORY]->(:Entity)--(phase)
       }
  })
  AND ($signatory_person_id IS NULL OR $signatory_person_id = '' OR EXISTS {
    MATCH (expr)-[:DESIGNATES_SIGNATORY]->(:Entity {entityId: $signatory_person_id})
  })
  AND ($since IS NULL OR effective_date >= $since)
  AND ($until IS NULL OR effective_date <= $until)
  AND coalesce(node.lifecycle_status, 'active') = 'active'
  AND coalesce(expr.lifecycle_status, 'active') = 'active'
  AND (item IS NULL OR coalesce(item.lifecycle_status, 'active') = 'active')
RETURN node.work_id AS work_id,
       node.title AS title,
       node.doc_type AS doc_type,
       item.inbox_filename AS file,
       effective_date AS effective_date,
       node.summary AS summary,
       score AS score
ORDER BY score DESC, effective_date DESC
LIMIT toInteger($limit)
""".strip()

SEARCH_CHUNKS_FULLTEXT_CYPHER = """
CALL db.index.fulltext.queryNodes('chunk_search', $query) YIELD node, score
MATCH (node)<-[:HAS_PART]-(expr:Expression)
MATCH (expr)<-[:HAS_REALIZATION]-(w:Work)
OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WHERE ($work_id IS NULL OR $work_id = '' OR w.work_id = $work_id)
  AND ($doc_type IS NULL OR $doc_type = '' OR w.doc_type = $doc_type)
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {
    MATCH (:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
    WHERE (expr)-[:MENTIONS|RECORDS|EVIDENCES|DESIGNATES_SIGNATORY]->(phase)
       OR EXISTS {
         MATCH (expr)-[:MENTIONS|RECORDS|EVIDENCES|DESIGNATES_SIGNATORY]->(:Entity)--(phase)
       }
  })
  AND coalesce(w.lifecycle_status, 'active') = 'active'
  AND coalesce(expr.lifecycle_status, 'active') = 'active'
  AND (item IS NULL OR coalesce(item.lifecycle_status, 'active') = 'active')
RETURN node.chunk_id AS chunk_id,
       node.sequence_index AS sequence_index,
       node.text AS text,
       node.page_first AS page_first,
       node.page_last AS page_last,
       node.structural_role AS structural_role,
       node.structural_path AS structural_path,
       w.work_id AS work_id,
       w.title AS work_title,
       w.doc_type AS doc_type,
       item.inbox_filename AS file,
       score AS score
ORDER BY score DESC, node.sequence_index ASC
LIMIT toInteger($limit)
""".strip()

CORPUS_OVERVIEW_CYPHER = """
CALL () { MATCH (w:Work) RETURN count(DISTINCT w) AS works }
CALL () { MATCH (e:Expression) RETURN count(DISTINCT e) AS expressions }
CALL () { MATCH (i:Item) RETURN count(DISTINCT i) AS items }
CALL () { MATCH (c:Chunk) RETURN count(DISTINCT c) AS chunks }
CALL () { MATCH (s:BusinessSubject) RETURN count(DISTINCT s) AS business_subjects }
CALL () { MATCH (p:Entity:Person) RETURN count(DISTINCT p) AS persons }
CALL () { MATCH (o:Entity:LegalEntity) RETURN count(DISTINCT o) AS organizations }
CALL () { MATCH (e:Entity:Event) RETURN count(DISTINCT e) AS events }
RETURN works, expressions, items, chunks, business_subjects, persons, organizations, events
""".strip()

LIST_BUSINESS_SUBJECTS_CYPHER = """
MATCH (subject:BusinessSubject)
OPTIONAL MATCH (subject)-[:HAS_PHASE]->(phase:Entity)
OPTIONAL MATCH (phase)<-[:MENTIONS|RECORDS|EVIDENCES|DESIGNATES_SIGNATORY]-(expr:Expression)
OPTIONAL MATCH (expr)<-[:HAS_REALIZATION]-(work:Work)
RETURN subject.subjectId AS subject_id,
       subject.label AS subject,
       count(DISTINCT phase) AS phase_count,
       [label IN collect(DISTINCT phase.label) WHERE label IS NOT NULL] AS phases,
       count(DISTINCT work) AS document_count
ORDER BY document_count DESC, subject ASC
LIMIT toInteger($limit)
""".strip()


def get_work(client: BaseGraphReader, *, work_id: str) -> dict[str, Any] | None:
    rows = client.read(GET_WORK_CYPHER, {"work_id": work_id})
    return rows[0] if rows else None


def read_chunks(
    client: BaseGraphReader,
    *,
    file: str | None,
    chunk_ids: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if file:
        document = fetch_document_source(client, file)
        if document is None:
            return []
        chunks = document.get("chunks") or []
        if not isinstance(chunks, list):
            return []
        return [chunk for chunk in chunks if isinstance(chunk, dict)][:limit]
    if not chunk_ids:
        return []
    return client.read(
        READ_CHUNKS_BY_ID_CYPHER,
        {"chunk_ids": chunk_ids, "limit": limit},
    )


def entity_mentions(
    client: BaseGraphReader,
    *,
    entity_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    return client.read(ENTITY_MENTIONS_CYPHER, {"entity_id": entity_id, "limit": limit})


def find_by_identifier(
    client: BaseGraphReader,
    *,
    value: str,
    kind: str | None,
) -> list[dict[str, Any]]:
    cleaned_value = value.strip()
    return client.read(
        FIND_BY_IDENTIFIER_CYPHER,
        {
            "value": cleaned_value,
            "allow_prefix": len(cleaned_value) >= 6,
            "kind": kind,
        },
    )


def search_documents_fulltext(
    client: BaseGraphReader,
    *,
    query: str,
    limit: int,
    doc_type: str | None = None,
    subject_id: str | None = None,
    signatory_person_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    return client.read(
        SEARCH_DOCUMENTS_FULLTEXT_CYPHER,
        {
            "query": query,
            "limit": limit,
            "doc_type": doc_type,
            "subject_id": subject_id,
            "signatory_person_id": signatory_person_id,
            "since": since,
            "until": until,
        },
    )


def search_chunks_fulltext(
    client: BaseGraphReader,
    *,
    query: str,
    limit: int,
    work_id: str | None = None,
    doc_type: str | None = None,
    subject_id: str | None = None,
) -> list[dict[str, Any]]:
    return client.read(
        SEARCH_CHUNKS_FULLTEXT_CYPHER,
        {
            "query": query,
            "limit": limit,
            "work_id": work_id,
            "doc_type": doc_type,
            "subject_id": subject_id,
        },
    )


def corpus_overview(client: BaseGraphReader) -> dict[str, int]:
    rows = client.read(CORPUS_OVERVIEW_CYPHER, {})
    if not rows:
        return {}
    return {key: int(value or 0) for key, value in rows[0].items()}


def list_business_subjects(
    client: BaseGraphReader,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    return client.read(LIST_BUSINESS_SUBJECTS_CYPHER, {"limit": limit})
