from typing import Any

from fastapi.testclient import TestClient

from corporate_rag.app.main import create_app
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.settings import AppSettings
from corporate_rag.workflows.engine import WorkflowEngine
from corporate_rag.workflows.models import Parameter, Workflow


class FakeGraphReader(BaseGraphReader):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((cypher, parameters))
        return [{"subject_id": parameters["subject_id"], "label": "AEH"}] if parameters else []


def test_workflow_catalog_endpoint_returns_categories_and_workflows() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.get("/api/workflows/catalog")

    assert response.status_code == 200
    assert response.json()["categories"] == ["General"]
    assert response.json()["workflows"][0]["workflow_id"] == "find.subject"
    assert "cypher" not in response.json()["workflows"][0]


def test_workflow_disclaimer_returns_document_count() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.get("/api/workflows/disclaimer")

    assert response.status_code == 200
    assert response.json() == {"document_count": 0}
    assert "count(DISTINCT w)" in reader.calls[0][0]


def test_workflow_typeahead_endpoint_returns_items() -> None:
    reader = TypeaheadGraphReader()
    client = build_client_with_catalog(reader, (build_workflow(),))

    response = client.get("/api/workflows/typeahead", params={"kind": "subject", "q": "acer"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "subject"
    assert payload["items"] == [
        {
            "id": "subject-aeh",
            "label": "Acer European Holdings",
            "hint": "family root",
            "edge_count": 5,
            "score": 1.5,
        }
    ]
    assert reader.calls[0][1]["lucene"] == "acer*"


def test_workflow_typeahead_rejects_unknown_kind() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.get("/api/workflows/typeahead", params={"kind": "unknown"})

    assert response.status_code == 400


def test_workflow_facet_endpoint_returns_counts() -> None:
    reader = FacetGraphReader()
    client = build_client_with_catalog(reader, (build_workflow(),))

    response = client.get(
        "/api/workflows/facet",
        params={
            "workflow_id": "documents.search",
            "parameter_name": "doc_type",
            "subject_id": "subject-aeh",
            "include_cancelled": "false",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"values": [{"value": "registry_extract", "count": 2}]}
    assert reader.calls[0][1]["subject_id"] == "subject-aeh"
    assert reader.calls[0][1]["include_cancelled"] is False


def test_workflow_evidence_endpoint_returns_chunks() -> None:
    reader = EvidenceGraphReader()
    client = build_client_with_catalog(reader, (build_workflow(),))

    response = client.post(
        "/api/workflows/evidence",
        json={
            "value": "1000000",
            "column": "amount",
            "files": ["registry.pdf"],
            "entity_id": "event-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["highlight_terms"] == [
        "1000000",
        "1,000,000",
        "1.000.000",
        "1'000'000",
        "1 000 000",
    ]
    assert payload["chunks"][0]["chunk_id"] == "chunk-1"
    assert reader.calls[0][1]["files"] == ["registry.pdf"]


def test_workflow_definition_endpoint_returns_one_workflow() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.get("/api/workflows/find.subject")

    assert response.status_code == 200
    assert response.json()["workflow_id"] == "find.subject"
    assert response.json()["parameters"][0]["name"] == "subject_id"
    assert "cypher" not in response.json()


def test_workflow_run_endpoint_executes_workflow() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.post(
        "/api/workflows/find.subject/run",
        json={"parameters": {"subject_id": "subject-aeh", "limit": "5"}},
    )

    assert response.status_code == 200
    assert reader.calls[0] == (
        "RETURN $subject_id AS subject_id",
        {"subject_id": "subject-aeh", "limit": 5},
    )
    assert len(reader.calls) == 3
    assert response.json()["rows"] == [{"subject_id": "subject-aeh", "label": "AEH"}]
    assert [table["table_id"] for table in response.json()["tables"]] == [
        "subject_phases",
        "subject_identifiers",
        "subject_board_history",
    ]
    assert "cypher" not in response.json()


def test_workflow_run_openapi_includes_swagger_examples() -> None:
    client = TestClient(create_app(AppSettings(environment="test"), configure_workflows=False))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/workflows/{workflow_id}/run"]["post"]
    workflow_id_parameter = operation["parameters"][0]
    examples = operation["requestBody"]["content"]["application/json"]["examples"]

    assert workflow_id_parameter["schema"]["examples"] == ["find.subject"]
    assert examples["find_subject"]["value"] == {
        "parameters": {
            "subject_id": "b096e064-e1cb-4ab8-b5bc-0c0e3729c696",
        }
    }
    assert examples["documents_search"]["value"] == {
        "parameters": {
            "doc_type": [],
            "signatory_person_id": "",
            "subject_id": "",
            "file": "",
            "text_query": "capital",
            "limit": 25,
        }
    }


def test_app_factory_configures_default_workflow_catalog() -> None:
    app = create_app(AppSettings(environment="test"))
    client = TestClient(app)

    response = client.get("/api/workflows/catalog")

    assert response.status_code == 200
    workflow_ids = [workflow["workflow_id"] for workflow in response.json()["workflows"]]
    assert "find.subject" in workflow_ids
    assert "documents.search" in workflow_ids


def test_workflow_run_endpoint_returns_400_for_bad_parameters() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.post(
        "/api/workflows/find.subject/run",
        json={"parameters": {"subject_id": "subject-aeh", "unknown": "value"}},
    )

    assert response.status_code == 400
    assert "Unknown parameter" in response.json()["detail"]


def test_workflow_endpoint_returns_404_for_unknown_workflow() -> None:
    reader = FakeGraphReader()
    client = build_client(reader)

    response = client.get("/api/workflows/missing.workflow")

    assert response.status_code == 404


def test_workflow_endpoint_returns_503_without_engine() -> None:
    client = TestClient(create_app(AppSettings(environment="test"), configure_workflows=False))

    response = client.get("/api/workflows/catalog")

    assert response.status_code == 503
    assert response.json()["detail"] == "workflow engine is not configured"


def build_client(reader: FakeGraphReader) -> TestClient:
    return build_client_with_catalog(reader, (build_workflow(),))


def build_client_with_catalog(
    reader: BaseGraphReader,
    catalog: tuple[Workflow, ...],
) -> TestClient:
    engine = WorkflowEngine(reader, catalog=catalog)
    app = create_app(AppSettings(environment="test"), workflow_engine=engine)
    return TestClient(app)


def build_workflow() -> Workflow:
    return Workflow(
        workflow_id="find.subject",
        title="Find subject",
        category="General",
        description="Find one subject.",
        cypher="RETURN $subject_id AS subject_id",
        parameters=(
            Parameter(name="subject_id", label="Subject", required=True),
            Parameter(name="limit", label="Limit", kind="number", default=10),
        ),
        output_columns=("subject_id", "label"),
    )


class TypeaheadGraphReader(BaseGraphReader):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        resolved_parameters = parameters or {}
        self.calls.append((cypher, resolved_parameters))
        return [
            {
                "id": "subject-aeh",
                "label": "Acer European Holdings",
                "hint": "family root",
                "edge_count": 5,
                "score": 1.5,
            }
        ]


class FacetGraphReader(BaseGraphReader):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        resolved_parameters = parameters or {}
        self.calls.append((cypher, resolved_parameters))
        return [{"value": "registry_extract", "count": 2}]


class EvidenceGraphReader(BaseGraphReader):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        resolved_parameters = parameters or {}
        self.calls.append((cypher, resolved_parameters))
        return [
            {
                "file": "registry.pdf",
                "chunk_id": "chunk-1",
                "text": "The capital amount is 1,000,000 shares.",
            }
        ]
