from typing import Any

from corporate_rag.graph.interfaces import BaseGraphReader


def fetch_document_source(client: BaseGraphReader, file: str) -> dict[str, Any] | None:
    rows = client.read(DOCUMENT_SOURCE_CYPHER, {"file": file})
    if not rows:
        return None

    row = rows[0]
    raw_chunks = row.get("raw_chunks") or []
    chunks = [chunk for chunk in raw_chunks if isinstance(chunk, dict)]
    return {
        "work_id": row.get("work_id"),
        "title": row.get("title"),
        "doc_type": row.get("doc_type"),
        "summary": row.get("summary"),
        "work_lifecycle_status": row.get("work_lifecycle_status"),
        "expression_lifecycle_status": row.get("expression_lifecycle_status"),
        "item_lifecycle_status": row.get("item_lifecycle_status"),
        "item_id": row.get("item_id"),
        "file": row.get("file"),
        "chunks": chunks,
    }


def fetch_document_titles(
    client: BaseGraphReader,
    files: list[str],
) -> dict[str, dict[str, Any]]:
    cleaned = [file.strip() for file in files if file.strip()]
    if not cleaned:
        return {}

    rows = client.read(DOCUMENT_TITLES_CYPHER, {"files": cleaned})
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        file = row.get("file")
        if file is None:
            continue
        metadata[str(file)] = {
            "work_id": row.get("work_id"),
            "title": row.get("title"),
            "doc_type": row.get("doc_type"),
            "work_lifecycle_status": row.get("work_lifecycle_status"),
            "expression_lifecycle_status": row.get("expression_lifecycle_status"),
            "item_lifecycle_status": row.get("item_lifecycle_status"),
            "item_id": row.get("item_id"),
            "file": row.get("inbox_filename"),
        }
    return metadata


DOCUMENT_SOURCE_CYPHER = """
MATCH (item:Item)
WHERE item.item_id = $file OR item.inbox_filename = $file
MATCH (item)<-[:HAS_EXEMPLAR]-(:Manifestation)
      <-[:HAS_EMBODIMENT]-(expr:Expression)
MATCH (expr)<-[:HAS_REALIZATION]-(work:Work)
OPTIONAL MATCH (expr)-[:HAS_PART]->(chunk:Chunk)
WITH item, work, expr, chunk
ORDER BY chunk.sequence_index
RETURN work.work_id AS work_id,
       work.title AS title,
       work.doc_type AS doc_type,
       work.summary AS summary,
       coalesce(work.lifecycle_status, 'active') AS work_lifecycle_status,
       coalesce(expr.lifecycle_status, 'active') AS expression_lifecycle_status,
       coalesce(item.lifecycle_status, 'active') AS item_lifecycle_status,
       item.item_id AS item_id,
       item.inbox_filename AS file,
       collect(
         CASE WHEN chunk IS NULL THEN NULL
         ELSE {
           chunk_id: chunk.chunk_id,
           sequence_index: chunk.sequence_index,
           structural_role: chunk.structural_role,
           structural_path: chunk.structural_path,
           page_first: chunk.page_first,
           page_last: chunk.page_last,
           text: chunk.text
         } END
       ) AS raw_chunks
LIMIT 1
""".strip()

DOCUMENT_TITLES_CYPHER = """
UNWIND $files AS file
MATCH (item:Item)
WHERE item.item_id = file OR item.inbox_filename = file
MATCH (item)<-[:HAS_EXEMPLAR]-(:Manifestation)
      <-[:HAS_EMBODIMENT]-(expr:Expression)
MATCH (expr)<-[:HAS_REALIZATION]-(work:Work)
WITH file, item, work, expr
RETURN file AS file,
       work.work_id AS work_id,
       work.title AS title,
       work.doc_type AS doc_type,
       coalesce(work.lifecycle_status, 'active') AS work_lifecycle_status,
       coalesce(expr.lifecycle_status, 'active') AS expression_lifecycle_status,
       coalesce(item.lifecycle_status, 'active') AS item_lifecycle_status,
       item.item_id AS item_id,
       item.inbox_filename AS inbox_filename
""".strip()
