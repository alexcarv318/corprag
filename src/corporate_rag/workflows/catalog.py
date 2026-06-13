from corporate_rag.workflows import repository
from corporate_rag.workflows.models import Parameter, Workflow, include_cancelled_parameter
from corporate_rag.workflows.options import DOCUMENT_TYPE_OPTIONS, EVENT_TYPE_OPTIONS


def typeahead_parameter(
    name: str,
    label: str,
    *,
    required: bool = False,
    default: str | None = "",
    placeholder: str | None = None,
    description: str = "",
) -> Parameter:
    return Parameter(
        name=name,
        label=label,
        description=description,
        kind="string",
        required=required,
        default=default,
        placeholder=placeholder,
    )


def date_parameter(name: str, label: str) -> Parameter:
    return Parameter(name=name, label=label, kind="date", default=None)


def limit_parameter(default: int = 100) -> Parameter:
    return Parameter(
        name="limit",
        label="Maximum results",
        description="How many rows to return at most.",
        kind="number",
        default=default,
    )


SUBJECT_ID = typeahead_parameter(
    "subject_id",
    "Business subject",
    required=True,
    default=None,
    placeholder="Search for a business subject...",
    description="Pick the business subject to inspect.",
)
OPTIONAL_SUBJECT_ID = typeahead_parameter(
    "subject_id",
    "Business subject",
    placeholder="Search for a business subject (optional)...",
    description="Leave blank to search across all business subjects.",
)
ORGANIZATION_ID = typeahead_parameter(
    "organization_id",
    "Organization",
    placeholder="Search for an organization (optional)...",
)
PERSON_ID = typeahead_parameter(
    "person_id",
    "Person",
    placeholder="Search for a person (optional)...",
)


FIND_SUBJECT = Workflow(
    workflow_id="find.subject",
    title="Find a business subject",
    category="General",
    description=(
        "Show the legal phases of one business subject, with identifiers and "
        "board history returned as detail tables."
    ),
    cypher=repository.SUBJECT_OVERVIEW,
    parameters=(SUBJECT_ID,),
    output_columns=(
        "subject_id",
        "subject",
        "phase_id",
        "phase_label",
        "phase_classes",
        "phase_valid_from",
        "phase_valid_to",
        "registration_number",
        "registration_scheme",
        "legal_form",
        "governing_law",
        "status",
        "registered_office",
        "sources",
    ),
    use_cases=(
        "Show every legal phase of this business subject.",
        "Find identifiers and board history for this business subject.",
    ),
)

FIND_ORGANIZATION = Workflow(
    workflow_id="find.organization",
    title="Find an organization",
    category="General",
    description=(
        "Browse or inspect legal entities and standalone organizations, with "
        "identifiers and registered offices returned for a focused organization."
    ),
    cypher=repository.ORGANIZATION_OVERVIEW,
    parameters=(ORGANIZATION_ID,),
    output_columns=(
        "organization_id",
        "label",
        "fibo_classes",
        "legal_names",
        "jurisdictions",
        "registered_offices",
        "registration_numbers",
        "date_of_incorporation",
        "date_of_dissolution",
        "mentions",
        "mention_count",
        "edge_count",
    ),
    use_cases=(
        "Look up a legal entity by name.",
        "Connect an organization back to a business-subject family.",
    ),
)

FIND_PERSON = Workflow(
    workflow_id="find.person",
    title="Find a person",
    category="General",
    description=(
        "Browse people or focus on one person. A focused person also returns "
        "roles and authority/document detail tables."
    ),
    cypher=repository.PERSON_OVERVIEW,
    parameters=(PERSON_ID,),
    output_columns=(
        "person_id",
        "person",
        "date_of_birth",
        "nationality",
        "residence",
        "passport",
        "mention_count",
        "mentions",
    ),
    use_cases=(
        "Confirm a person's identity.",
        "Find a person's roles, authority, and signed documents.",
    ),
)

DOCUMENTS_SEARCH = Workflow(
    workflow_id="documents.search",
    title="Find documents",
    category="General",
    description=(
        "Search documents by type, signatory, business subject, filename, "
        "or keyword."
    ),
    cypher=repository.DOCUMENTS_SEARCH,
    parameters=(
        Parameter(
            name="doc_type",
            label="Document type",
            kind="select",
            options=DOCUMENT_TYPE_OPTIONS,
            multiple=True,
            default=(),
        ),
        typeahead_parameter(
            "signatory_person_id",
            "Signed by",
            placeholder="Search for a person (optional)...",
        ),
        OPTIONAL_SUBJECT_ID,
        typeahead_parameter(
            "file",
            "Filename",
            placeholder="Search for a document (optional)...",
        ),
        Parameter(
            name="text_query",
            label="Keyword",
            kind="string",
            default="",
            placeholder="e.g. capital injection",
        ),
        limit_parameter(),
    ),
    output_columns=(
        "work_id",
        "expression_id",
        "item_id",
        "title",
        "doc_type",
        "effective_date",
        "work_lifecycle_status",
        "expression_lifecycle_status",
        "item_lifecycle_status",
        "summary",
        "sources",
    ),
    use_cases=(
        "Find documents signed by a person.",
        "Find documents about a business subject.",
    ),
)

CAPITAL_SHAREHOLDINGS = Workflow(
    workflow_id="capital.shareholdings",
    title="Capital and shareholdings",
    category="General",
    description=(
        "Show capital-related events and, when available, a holder detail table."
    ),
    cypher=repository.CAPITAL_EVENTS,
    parameters=(
        OPTIONAL_SUBJECT_ID,
        ORGANIZATION_ID,
        date_parameter("since", "From date"),
        date_parameter("until", "To date"),
        Parameter(
            name="event_type",
            label="Event type",
            kind="select",
            options=EVENT_TYPE_OPTIONS,
            default="",
        ),
        limit_parameter(100),
    ),
    output_columns=(
        "subject",
        "effective_date",
        "event",
        "event_type",
        "acting_parties",
        "affected_parties",
        "counterparties",
        "amount",
        "currency",
        "monetary_amount_id",
        "primary_document_type",
        "authority_status",
        "source_documents",
        "sources",
        "event_id",
    ),
    use_cases=(
        "Show share issues, transfers, and capital changes.",
        "Review holder rows for one organization.",
    ),
)

POA_REGISTER = Workflow(
    workflow_id="governance.poa.register",
    title="Powers of attorney",
    category="General",
    description=(
        "Show powers of attorney by business subject, organization, or person."
    ),
    cypher=repository.POA_REGISTER,
    parameters=(
        OPTIONAL_SUBJECT_ID,
        typeahead_parameter(
            "involves_organization_id",
            "Organization",
            placeholder="Search for an organization (optional)...",
        ),
        typeahead_parameter(
            "involves_person_id",
            "Person",
            placeholder="Search for a person (optional)...",
        ),
        include_cancelled_parameter(),
    ),
    output_columns=(
        "subject",
        "phase_id",
        "phase",
        "phase_valid_from",
        "phase_valid_to",
        "poa_id",
        "poa_label",
        "scope",
        "signature_mode",
        "valid_from",
        "valid_to",
        "valid_to_event_id",
        "lifecycle_status",
        "revocation_terms",
        "grounding_quote",
        "grantee_persons",
        "firm_grantees",
        "authorizing_parties",
        "concerned_organizations",
        "supporting_titles",
        "sources",
    ),
    use_cases=(
        "Which powers of attorney are active?",
        "Who received authority to act?",
    ),
)

EVENTS_TIMELINE = Workflow(
    workflow_id="events.timeline",
    title="Event timeline",
    category="General",
    description=(
        "Search corporate events by subject, participant, event type, keyword, "
        "or date range."
    ),
    cypher=repository.EVENTS_TIMELINE,
    parameters=(
        OPTIONAL_SUBJECT_ID,
        typeahead_parameter(
            "participant_id",
            "Participant",
            placeholder="Search for an organization (optional)...",
        ),
        Parameter(
            name="event_type",
            label="Event type",
            kind="select",
            options=EVENT_TYPE_OPTIONS,
            default="",
        ),
        Parameter(name="q", label="Keyword", kind="string", default=""),
        date_parameter("since", "From date"),
        date_parameter("until", "To date"),
        limit_parameter(100),
    ),
    output_columns=(
        "actors",
        "undergoers",
        "event",
        "event_type",
        "event_domain",
        "effective_date",
        "primary_document_type",
        "authority_status",
        "counterparties",
        "amount",
        "currency",
        "sources",
        "supporting_titles",
        "subject",
        "event_id",
    ),
    use_cases=(
        "Build a chronology of corporate events.",
        "Find events involving a subject or participant.",
    ),
)

DATA_MODEL_GUIDE = Workflow(
    workflow_id="data_model.guide",
    title="Data model",
    category="Data model",
    description="Short guide to the graph concepts used by the workflow backend.",
    cypher=repository.DATA_MODEL_GUIDE,
    output_columns=("section",),
    use_cases=("Understand the graph model behind the workflow console.",),
)

DATA_MODEL_DEV_WORKFLOWS = Workflow(
    workflow_id="data_model.dev_workflows",
    title="Data model classes",
    category="Data model",
    description="Developer-only class glossary lookup.",
    cypher=repository.DATA_MODEL_CLASSES,
    parameters=(
        Parameter(name="query", label="Keyword", kind="string", default=""),
        limit_parameter(500),
    ),
    output_columns=("section",),
    use_cases=("Inspect schema class names and definitions.",),
    dev_only=True,
)

CATALOG: tuple[Workflow, ...] = (
    FIND_SUBJECT,
    FIND_ORGANIZATION,
    FIND_PERSON,
    DOCUMENTS_SEARCH,
    CAPITAL_SHAREHOLDINGS,
    POA_REGISTER,
    EVENTS_TIMELINE,
    DATA_MODEL_GUIDE,
    DATA_MODEL_DEV_WORKFLOWS,
)

_INDEX: dict[str, Workflow] = {workflow.workflow_id: workflow for workflow in CATALOG}


def by_id(workflow_id: str) -> Workflow:
    if workflow_id not in _INDEX:
        raise KeyError(f"Unknown workflow_id: {workflow_id!r}")
    return _INDEX[workflow_id]


def categories() -> list[str]:
    result: list[str] = []
    for workflow in CATALOG:
        if workflow.category not in result:
            result.append(workflow.category)
    return result
