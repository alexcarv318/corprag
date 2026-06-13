from corporate_rag.workflows.models import (
    Parameter,
    Workflow,
    WorkflowResult,
    include_cancelled_parameter,
)


def test_parameter_serializes_for_api_contract() -> None:
    parameter = Parameter(
        name="subject_id",
        label="Subject",
        description="Canonical subject id.",
        required=True,
        placeholder="Pick a subject",
    )

    assert parameter.to_dict() == {
        "name": "subject_id",
        "label": "Subject",
        "description": "Canonical subject id.",
        "kind": "string",
        "required": True,
        "default": None,
        "options": None,
        "placeholder": "Pick a subject",
        "multiple": False,
        "gated_default": False,
    }


def test_workflow_serializes_for_catalog_contract() -> None:
    workflow = Workflow(
        workflow_id="find.subject",
        title="Find subject",
        category="General",
        description="Find one corporate subject.",
        cypher="RETURN $subject_id AS subject_id",
        parameters=(Parameter(name="subject_id", label="Subject", required=True),),
        output_columns=("subject_id",),
        use_cases=("Resolve subject before downstream workflows.",),
    )

    payload = workflow.to_dict()

    assert payload["workflow_id"] == "find.subject"
    assert payload["parameters"][0]["name"] == "subject_id"
    assert payload["output_columns"] == ["subject_id"]
    assert payload["use_cases"] == ["Resolve subject before downstream workflows."]


def test_workflow_result_adds_default_table_payload() -> None:
    result = WorkflowResult(
        workflow_id="find.subject",
        parameters={"subject_id": "subject-aeh"},
        rows=[{"subject_id": "subject-aeh"}],
        columns=["subject_id"],
        row_count=1,
        elapsed_ms=1.0,
        cypher="RETURN 1",
    )

    payload = result.to_dict()

    assert payload["tables"] == [
        {
            "table_id": "find.subject",
            "title": "Results",
            "rows": [{"subject_id": "subject-aeh"}],
            "columns": ["subject_id"],
            "row_count": 1,
        }
    ]


def test_include_cancelled_parameter_is_boolean_default_false() -> None:
    parameter = include_cancelled_parameter()

    assert parameter.name == "include_cancelled"
    assert parameter.kind == "boolean"
    assert parameter.default is False
