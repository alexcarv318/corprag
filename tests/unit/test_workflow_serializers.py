from corporate_rag.workflows.models import Parameter, Workflow, WorkflowResult
from corporate_rag.workflows.serializers import (
    workflow_public_payload,
    workflow_result_public_payload,
)


def test_workflow_public_payload_includes_cypher() -> None:
    workflow = Workflow(
        workflow_id="find.subject",
        title="Find subject",
        category="General",
        description="Find one subject.",
        cypher="MATCH (n) RETURN n",
        parameters=(Parameter(name="subject_id", label="Subject"),),
        output_columns=("subject_id",),
    )

    payload = workflow_public_payload(workflow)

    assert payload["workflow_id"] == "find.subject"
    assert payload["parameters"][0]["name"] == "subject_id"
    assert payload["cypher"] == "MATCH (n) RETURN n"


def test_workflow_result_public_payload_includes_cypher() -> None:
    result = WorkflowResult(
        workflow_id="find.subject",
        parameters={"subject_id": "subject-aeh"},
        rows=[{"subject_id": "subject-aeh"}],
        columns=["subject_id"],
        row_count=1,
        elapsed_ms=1.0,
        cypher="MATCH (n) RETURN n",
    )

    payload = workflow_result_public_payload(result)

    assert payload["workflow_id"] == "find.subject"
    assert payload["rows"] == [{"subject_id": "subject-aeh"}]
    assert payload["cypher"] == "MATCH (n) RETURN n"
