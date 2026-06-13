from datetime import date
from typing import Any

import pytest

from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.workflows.engine import (
    WorkflowEngine,
    coerce_workflow_value,
    resolve_typeahead_kind_for_parameter,
)
from corporate_rag.workflows.models import Parameter, Workflow


class SequencedGraphReader(BaseGraphReader):
    def __init__(self, responses: list[list[dict[str, Any]]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((cypher, parameters))
        if not self.responses:
            return []
        return self.responses.pop(0)


class FakeGraphReader(BaseGraphReader):
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((cypher, parameters))
        return self.rows


def test_engine_lists_and_resolves_workflows() -> None:
    workflow = build_test_workflow()
    engine = WorkflowEngine(FakeGraphReader([]), catalog=(workflow,))

    assert engine.list_workflows() == [workflow]
    assert engine.get_workflow("test.workflow") == workflow


def test_engine_rejects_unknown_workflow_id() -> None:
    engine = WorkflowEngine(FakeGraphReader([]), catalog=(build_test_workflow(),))

    with pytest.raises(KeyError):
        engine.get_workflow("missing.workflow")


def test_engine_runs_workflow_with_coerced_parameters_and_normalized_rows() -> None:
    workflow = build_test_workflow()
    reader = FakeGraphReader(
        rows=[
            {"name": "Older", "effective_date": date(2020, 1, 1), "count": 2},
            {"name": "Newer", "effective_date": date(2021, 1, 1), "count": 3},
        ]
    )
    engine = WorkflowEngine(reader, catalog=(workflow,))

    result = engine.run(
        "test.workflow",
        {
            "subject_id": "subject-aeh",
            "limit": "5",
            "include_cancelled": "true",
            "doc_types": ["share_certificate", "all", ""],
        },
    )

    assert reader.calls == [
        (
            "RETURN $subject_id AS subject_id",
            {
                "subject_id": "subject-aeh",
                "limit": 5,
                "include_cancelled": True,
                "doc_types": ["share_certificate"],
            },
        )
    ]
    assert result.columns == ["name", "effective_date", "count"]
    assert result.rows == [
        {"name": "Newer", "effective_date": "2021-01-01", "count": 3},
        {"name": "Older", "effective_date": "2020-01-01", "count": 2},
    ]
    assert result.row_count == 2


def test_engine_rejects_unknown_parameters() -> None:
    engine = WorkflowEngine(FakeGraphReader([]), catalog=(build_test_workflow(),))

    with pytest.raises(ValueError, match="Unknown parameter"):
        engine.run("test.workflow", {"unknown": "value"})


def test_engine_rejects_missing_required_parameter() -> None:
    workflow = Workflow(
        workflow_id="required.workflow",
        title="Required workflow",
        category="Test",
        description="Requires subject.",
        cypher="RETURN $subject_id AS subject_id",
        parameters=(Parameter(name="subject_id", label="Subject", required=True),),
    )
    engine = WorkflowEngine(FakeGraphReader([]), catalog=(workflow,))

    with pytest.raises(ValueError, match="Missing required parameter"):
        engine.run("required.workflow")


@pytest.mark.parametrize(
    ("parameter", "expected_kind"),
    [
        (Parameter(name="subject_id", label="Subject"), "subject"),
        (Parameter(name="signatory_person_id", label="Person"), "person"),
        (Parameter(name="participant_id", label="Participant"), "organization"),
        (Parameter(name="file", label="File"), "file"),
        (Parameter(name="source_filename", label="Filename"), "file"),
        (Parameter(name="random_id", label="Random"), None),
        (Parameter(name="subject_id", label="Subject", kind="select"), None),
    ],
)
def test_resolve_typeahead_kind_for_parameter(
    parameter: Parameter,
    expected_kind: str | None,
) -> None:
    assert resolve_typeahead_kind_for_parameter(parameter) == expected_kind


def test_coerce_workflow_value_preserves_empty_date_default() -> None:
    parameter = Parameter(name="since", label="Since", kind="date", default=None)

    assert coerce_workflow_value(parameter, "") is None
    assert coerce_workflow_value(parameter, "2015-01-01") == "2015-01-01"


def test_coerce_workflow_value_rejects_invalid_number() -> None:
    parameter = Parameter(name="limit", label="Limit", kind="number")

    with pytest.raises(ValueError, match="expected a number"):
        coerce_workflow_value(parameter, "many")


def build_test_workflow() -> Workflow:
    return Workflow(
        workflow_id="test.workflow",
        title="Test workflow",
        category="Test",
        description="A workflow for engine tests.",
        cypher="RETURN $subject_id AS subject_id",
        parameters=(
            Parameter(name="subject_id", label="Subject", required=True),
            Parameter(name="limit", label="Limit", kind="number", default=10),
            Parameter(
                name="include_cancelled",
                label="Include cancelled",
                kind="boolean",
                default=False,
            ),
            Parameter(name="doc_types", label="Document types", kind="select", multiple=True),
        ),
        output_columns=("name", "effective_date", "count"),
    )


def test_find_subject_returns_ui_detail_tables() -> None:
    workflow = Workflow(
        workflow_id="find.subject",
        title="Find subject",
        category="General",
        description="Find one subject.",
        cypher="subject cypher",
        parameters=(Parameter(name="subject_id", label="Subject", required=True),),
        output_columns=("subject_id", "subject"),
    )
    reader = SequencedGraphReader(
        [
            [{"subject_id": "subject-aeh", "subject": "AEH"}],
            [{"identifier": "CHE-123", "kind": "RegistrationIdentifier"}],
            [{"person": "Jane", "role": "Director"}],
        ]
    )
    engine = WorkflowEngine(reader, catalog=(workflow,))

    result = engine.run("find.subject", {"subject_id": "subject-aeh"})

    assert [table.table_id for table in result.tables] == [
        "subject_phases",
        "subject_identifiers",
        "subject_board_history",
    ]
    assert result.tables[0].rows == [{"subject_id": "subject-aeh", "subject": "AEH"}]
    assert result.tables[1].rows == [{"identifier": "CHE-123", "kind": "RegistrationIdentifier"}]
    assert result.tables[2].rows == [{"person": "Jane", "role": "Director"}]
    assert len(reader.calls) == 3
    assert reader.calls[1][1] == {"subject_id": "subject-aeh"}


def test_find_person_browse_stays_single_table() -> None:
    workflow = Workflow(
        workflow_id="find.person",
        title="Find person",
        category="General",
        description="Find a person.",
        cypher="person cypher",
        parameters=(Parameter(name="person_id", label="Person"),),
        output_columns=("person_id", "person"),
    )
    reader = SequencedGraphReader([[{"person_id": "p1", "person": "Jane"}]])
    engine = WorkflowEngine(reader, catalog=(workflow,))

    result = engine.run("find.person")

    assert result.tables == ()
    assert result.rows == [{"person_id": "p1", "person": "Jane"}]
    assert len(reader.calls) == 1


def test_find_person_focus_returns_ui_detail_tables() -> None:
    workflow = Workflow(
        workflow_id="find.person",
        title="Find person",
        category="General",
        description="Find a person.",
        cypher="person cypher",
        parameters=(Parameter(name="person_id", label="Person"),),
        output_columns=("person_id", "person"),
    )
    reader = SequencedGraphReader(
        [
            [{"person_id": "p1", "person": "Jane"}],
            [{"role": "Director"}],
            [{"branch": "authority"}],
        ]
    )
    engine = WorkflowEngine(reader, catalog=(workflow,))

    result = engine.run("find.person", {"person_id": "p1"})

    assert [table.table_id for table in result.tables] == [
        "person",
        "person_roles_and_affiliations",
        "person_authority_and_documents",
    ]
    assert result.tables[1].rows == [{"role": "Director"}]
    assert result.tables[2].rows == [{"branch": "authority"}]
    assert reader.calls[2][1] == {"person_id": "p1", "include_cancelled": True}
