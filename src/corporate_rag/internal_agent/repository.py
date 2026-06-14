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
