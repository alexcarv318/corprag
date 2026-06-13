from typing import Any

from fastapi.testclient import TestClient

from corporate_rag.app.main import create_app
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.settings import AppSettings


class DocumentGraphReader(BaseGraphReader):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((cypher, parameters))
        if parameters == {"file": "registry.pdf"}:
            return [
                {
                    "work_id": "work-1",
                    "title": "Registry Extract",
                    "doc_type": "registry_extract",
                    "summary": "Company registry extract.",
                    "work_lifecycle_status": "active",
                    "expression_lifecycle_status": "active",
                    "item_lifecycle_status": "active",
                    "item_id": "item-1",
                    "file": "registry.pdf",
                    "raw_chunks": [
                        {
                            "chunk_id": "chunk-1",
                            "sequence_index": 1,
                            "structural_role": "paragraph",
                            "structural_path": "page[1]/paragraph[1]",
                            "page_first": 1,
                            "page_last": 1,
                            "text": "Registry text.",
                        }
                    ],
                }
            ]
        if parameters == {"files": ["registry.pdf"]}:
            return [
                {
                    "file": "registry.pdf",
                    "work_id": "work-1",
                    "title": "Registry Extract",
                    "doc_type": "registry_extract",
                    "work_lifecycle_status": "active",
                    "expression_lifecycle_status": "active",
                    "item_lifecycle_status": "active",
                    "item_id": "item-1",
                    "inbox_filename": "registry.pdf",
                }
            ]
        return []


def test_document_source_endpoint_returns_chunks() -> None:
    reader = DocumentGraphReader()
    client = build_client(reader)

    response = client.get("/api/documents/source", params={"file": "registry.pdf"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Registry Extract"
    assert payload["chunks"][0]["chunk_id"] == "chunk-1"


def test_document_source_endpoint_returns_404_for_missing_document() -> None:
    client = build_client(DocumentGraphReader())

    response = client.get("/api/documents/source", params={"file": "missing.pdf"})

    assert response.status_code == 404


def test_document_titles_endpoint_returns_metadata_by_requested_file() -> None:
    client = build_client(DocumentGraphReader())

    response = client.get("/api/documents/titles", params={"file": "registry.pdf"})

    assert response.status_code == 200
    assert response.json()["titles"]["registry.pdf"]["title"] == "Registry Extract"


def build_client(reader: BaseGraphReader) -> TestClient:
    app = create_app(
        AppSettings(environment="test"),
        graph_reader=reader,
        configure_workflows=False,
    )
    return TestClient(app)
