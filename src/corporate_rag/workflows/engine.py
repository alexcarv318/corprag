import time
from datetime import date, datetime
from typing import Any

from neo4j.time import Date as Neo4jDate
from neo4j.time import DateTime as Neo4jDateTime

from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.workflows import repository
from corporate_rag.workflows.models import (
    Parameter,
    Workflow,
    WorkflowResult,
    WorkflowResultTable,
)

DATE_SORT_PRIORITY: tuple[str, ...] = (
    "valid_from",
    "phase_valid_from",
    "effective_date",
    "as_of",
    "term_start",
    "date_of_incorporation",
    "valid_to",
    "phase_valid_to",
    "term_end",
)

TYPEAHEAD_KIND_BY_PARAMETER_SUFFIX: tuple[tuple[str, str], ...] = (
    ("subject_id", "subject"),
    ("person_id", "person"),
    ("phase_id", "phase"),
    ("event_id", "event"),
    ("work_id", "work"),
    ("organization_id", "organization"),
    ("participant_id", "organization"),
    ("class_id", "class"),
    ("module", "module"),
)


class WorkflowEngine:
    def __init__(self, client: BaseGraphReader, catalog: tuple[Workflow, ...]) -> None:
        self.client = client
        self.catalog = tuple(catalog)
        self.index = {workflow.workflow_id: workflow for workflow in self.catalog}

    def list_workflows(self) -> list[Workflow]:
        return list(self.catalog)

    def get_workflow(self, workflow_id: str) -> Workflow:
        if workflow_id not in self.index:
            raise KeyError(f"Unknown workflow_id: {workflow_id!r}")
        return self.index[workflow_id]

    def run(
        self,
        workflow_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        workflow = self.get_workflow(workflow_id)
        coerced_parameters = self.build_parameters(workflow, parameters or {})

        if workflow.workflow_id == "find.subject":
            return self.run_find_subject_workflow(workflow, coerced_parameters)
        if workflow.workflow_id == "find.person":
            return self.run_find_person_workflow(workflow, coerced_parameters)
        if workflow.workflow_id == "find.organization":
            return self.run_find_organization_workflow(workflow, coerced_parameters)
        if workflow.workflow_id == "capital.shareholdings":
            return self.run_capital_workflow(workflow, coerced_parameters)

        return self.run_single_table_workflow(workflow, coerced_parameters)

    def build_parameters(
        self,
        workflow: Workflow,
        supplied_parameters: dict[str, Any],
    ) -> dict[str, Any]:
        known_parameters = {parameter.name for parameter in workflow.parameters}
        unknown_parameters = set(supplied_parameters) - known_parameters
        if unknown_parameters:
            unknown = ", ".join(sorted(unknown_parameters))
            raise ValueError(f"Unknown parameter(s) for {workflow.workflow_id}: {unknown}")

        result: dict[str, Any] = {}
        for parameter in workflow.parameters:
            raw_value = supplied_parameters.get(parameter.name, parameter.default)
            coerced_value = coerce_workflow_value(parameter, raw_value)
            if parameter.required and (coerced_value is None or coerced_value == ""):
                raise ValueError(f"Missing required parameter: {parameter.name}")
            result[parameter.name] = coerced_value

        return result

    def derive_columns(
        self,
        workflow: Workflow,
        rows: list[dict[str, Any]],
    ) -> list[str]:
        if workflow.output_columns:
            return list(workflow.output_columns)
        if not rows:
            return []
        return list(rows[0].keys())

    def read_normalized(
        self,
        cypher: str,
        parameters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return normalize_and_sort_rows(self.client.read(cypher, parameters))

    def run_single_table_workflow(
        self,
        workflow: Workflow,
        coerced_parameters: dict[str, Any],
    ) -> WorkflowResult:
        started_at = time.perf_counter()
        rows = self.client.read(workflow.cypher, coerced_parameters)
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        normalized_rows = normalize_and_sort_rows(rows)
        columns = self.derive_columns(workflow, normalized_rows)

        return WorkflowResult(
            workflow_id=workflow.workflow_id,
            parameters=coerced_parameters,
            rows=normalized_rows,
            columns=columns,
            row_count=len(normalized_rows),
            elapsed_ms=elapsed_ms,
            cypher=workflow.cypher,
        )

    def run_find_subject_workflow(
        self,
        workflow: Workflow,
        coerced_parameters: dict[str, Any],
    ) -> WorkflowResult:
        subject_parameters = {"subject_id": coerced_parameters["subject_id"]}
        started_at = time.perf_counter()
        primary_rows = self.read_normalized(workflow.cypher, coerced_parameters)
        identifier_rows = self.read_normalized(
            repository.SUBJECT_IDENTIFIERS,
            subject_parameters,
        )
        board_rows = self.read_normalized(
            repository.SUBJECT_BOARD_HISTORY,
            subject_parameters,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        primary_columns = self.derive_columns(workflow, primary_rows)
        identifier_columns = columns_or_default(
            identifier_rows,
            list(repository.SUBJECT_IDENTIFIER_COLUMNS),
        )
        board_columns = columns_or_default(
            board_rows,
            list(repository.SUBJECT_BOARD_HISTORY_COLUMNS),
        )
        tables = (
            WorkflowResultTable(
                table_id="subject_phases",
                title="Organizations (phases)",
                rows=primary_rows,
                columns=primary_columns,
                row_count=len(primary_rows),
            ),
            WorkflowResultTable(
                table_id="subject_identifiers",
                title="Identifiers",
                rows=identifier_rows,
                columns=identifier_columns,
                row_count=len(identifier_rows),
            ),
            WorkflowResultTable(
                table_id="subject_board_history",
                title="Board history",
                rows=board_rows,
                columns=board_columns,
                row_count=len(board_rows),
            ),
        )
        return workflow_result_with_tables(
            workflow, coerced_parameters, primary_rows, primary_columns, elapsed_ms, tables
        )

    def run_find_person_workflow(
        self,
        workflow: Workflow,
        coerced_parameters: dict[str, Any],
    ) -> WorkflowResult:
        person_id = coerced_parameters.get("person_id")
        if not person_id:
            return self.run_single_table_workflow(workflow, coerced_parameters)

        started_at = time.perf_counter()
        primary_rows = self.read_normalized(workflow.cypher, coerced_parameters)
        roles_rows = self.read_normalized(repository.PERSON_ROLES, {"person_id": person_id})
        authority_rows = self.read_normalized(
            repository.PERSON_AUTHORITY,
            {"person_id": person_id, "include_cancelled": True},
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        primary_columns = self.derive_columns(workflow, primary_rows)
        tables = (
            WorkflowResultTable(
                table_id="person",
                title="Person",
                rows=primary_rows,
                columns=primary_columns,
                row_count=len(primary_rows),
            ),
            WorkflowResultTable(
                table_id="person_roles_and_affiliations",
                title="Person roles and affiliations",
                rows=roles_rows,
                columns=list(repository.PERSON_ROLE_COLUMNS),
                row_count=len(roles_rows),
            ),
            WorkflowResultTable(
                table_id="person_authority_and_documents",
                title="Person authority and documents",
                rows=authority_rows,
                columns=list(repository.PERSON_AUTHORITY_COLUMNS),
                row_count=len(authority_rows),
            ),
        )
        return workflow_result_with_tables(
            workflow, coerced_parameters, primary_rows, primary_columns, elapsed_ms, tables
        )

    def run_find_organization_workflow(
        self,
        workflow: Workflow,
        coerced_parameters: dict[str, Any],
    ) -> WorkflowResult:
        organization_id = coerced_parameters.get("organization_id")
        if not organization_id:
            return self.run_single_table_workflow(workflow, coerced_parameters)

        organization_parameters = {"organization_id": organization_id}
        started_at = time.perf_counter()
        primary_rows = self.read_normalized(workflow.cypher, coerced_parameters)
        identifier_rows = self.read_normalized(
            repository.ORGANIZATION_IDENTIFIERS,
            organization_parameters,
        )
        office_rows = self.read_normalized(
            repository.ORGANIZATION_OFFICES,
            organization_parameters,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        primary_columns = self.derive_columns(workflow, primary_rows)
        tables: list[WorkflowResultTable] = [
            WorkflowResultTable(
                table_id="organization",
                title="Organization",
                rows=primary_rows,
                columns=primary_columns,
                row_count=len(primary_rows),
            )
        ]
        if identifier_rows:
            tables.append(
                WorkflowResultTable(
                    table_id="organization_identifiers",
                    title="Identifiers",
                    rows=identifier_rows,
                    columns=list(repository.ORGANIZATION_IDENTIFIER_COLUMNS),
                    row_count=len(identifier_rows),
                )
            )
        if office_rows:
            tables.append(
                WorkflowResultTable(
                    table_id="organization_offices",
                    title="Registered offices",
                    rows=office_rows,
                    columns=list(repository.ORGANIZATION_OFFICE_COLUMNS),
                    row_count=len(office_rows),
                )
            )
        return workflow_result_with_tables(
            workflow, coerced_parameters, primary_rows, primary_columns, elapsed_ms, tuple(tables)
        )

    def run_capital_workflow(
        self,
        workflow: Workflow,
        coerced_parameters: dict[str, Any],
    ) -> WorkflowResult:
        query_parameters = dict(coerced_parameters)
        query_parameters.setdefault("as_of", "")
        started_at = time.perf_counter()
        primary_rows = self.read_normalized(
            repository.CAPITAL_EVENTS,
            query_parameters,
        )
        holder_rows = self.read_normalized(
            repository.CAPITAL_HOLDERS,
            query_parameters,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        primary_columns = self.derive_columns(workflow, primary_rows)
        tables: list[WorkflowResultTable] = [
            WorkflowResultTable(
                table_id="capital_events",
                title="Capital events",
                rows=primary_rows,
                columns=primary_columns,
                row_count=len(primary_rows),
            )
        ]
        if holder_rows:
            tables.append(
                WorkflowResultTable(
                    table_id="capital_holders",
                    title="Holders",
                    rows=holder_rows,
                    columns=list(repository.CAPITAL_HOLDER_COLUMNS),
                    row_count=len(holder_rows),
                )
            )
        return workflow_result_with_tables(
            workflow, coerced_parameters, primary_rows, primary_columns, elapsed_ms, tuple(tables)
        )


def columns_or_default(rows: list[dict[str, Any]], default: list[str]) -> list[str]:
    if rows:
        return list(rows[0].keys())
    return default


def workflow_result_with_tables(
    workflow: Workflow,
    parameters: dict[str, Any],
    rows: list[dict[str, Any]],
    columns: list[str],
    elapsed_ms: float,
    tables: tuple[WorkflowResultTable, ...],
) -> WorkflowResult:
    return WorkflowResult(
        workflow_id=workflow.workflow_id,
        parameters=parameters,
        rows=rows,
        columns=columns,
        row_count=len(rows),
        elapsed_ms=elapsed_ms,
        cypher=workflow.cypher,
        tables=tables,
    )


def resolve_typeahead_kind_for_parameter(parameter: Parameter) -> str | None:
    if parameter.kind != "string":
        return None

    name = parameter.name
    for suffix, kind in TYPEAHEAD_KIND_BY_PARAMETER_SUFFIX:
        if name == suffix or name.endswith("_" + suffix):
            return kind

    if name == "file" or name.endswith("_filename"):
        return "file"

    return None


def coerce_workflow_value(parameter: Parameter, raw_value: Any) -> Any:
    if parameter.kind == "select" and parameter.multiple:
        return coerce_multiple_select_value(raw_value)

    if raw_value is None or raw_value == "":
        return parameter.default

    if parameter.kind == "number":
        return coerce_number_value(parameter, raw_value)

    if parameter.kind == "boolean":
        return coerce_boolean_value(raw_value)

    if parameter.kind == "date":
        return coerce_date_value(parameter, raw_value)

    return str(raw_value)


def coerce_multiple_select_value(raw_value: Any) -> list[str]:
    if raw_value is None or raw_value == "":
        return []

    if isinstance(raw_value, (list, tuple, set)):
        values = raw_value
    else:
        values = [raw_value]

    return [
        str(value)
        for value in values
        if value is not None and str(value) not in {"", "all"}
    ]


def coerce_number_value(parameter: Parameter, raw_value: Any) -> int | float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Parameter {parameter.name!r} expected a number, got {raw_value!r}"
        ) from exc

    return int(value) if value.is_integer() else value


def coerce_boolean_value(raw_value: Any) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw_value)


def coerce_date_value(parameter: Parameter, raw_value: Any) -> str | None:
    if isinstance(raw_value, (date, datetime)):
        return raw_value.strftime("%Y-%m-%d")

    text = str(raw_value).strip()
    if not text:
        return None if parameter.default is None else str(parameter.default)

    if text.lower() == "today":
        return date.today().strftime("%Y-%m-%d")

    return text


def normalize_workflow_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (Neo4jDate, Neo4jDateTime, date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalize_workflow_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize_workflow_value(item) for item in value]
    return str(value)


def normalize_and_sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = [
        {key: normalize_workflow_value(value) for key, value in row.items()}
        for row in rows
    ]
    return sort_rows_by_date_desc(normalized_rows)


def sort_rows_by_date_desc(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    column = pick_date_sort_column(rows)
    if column is None:
        return rows

    return sorted(
        rows,
        key=lambda row: (row.get(column) not in (None, ""), str(row.get(column) or "")),
        reverse=True,
    )


def pick_date_sort_column(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None

    row_keys: set[str] = set()
    for row in rows:
        row_keys.update(row.keys())

    for column in DATE_SORT_PRIORITY:
        if column not in row_keys:
            continue
        if any(row.get(column) not in (None, "") for row in rows):
            return column

    return None
