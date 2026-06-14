from corporate_rag.workflows.catalog import CATALOG, by_id, categories


def test_workflow_catalog_contains_current_product_surface() -> None:
    workflow_ids = [workflow.workflow_id for workflow in CATALOG]

    assert workflow_ids == [
        "find.subject",
        "find.organization",
        "find.person",
        "documents.search",
        "capital.shareholdings",
        "governance.poa.register",
        "events.timeline",
        "data_model.guide",
        "data_model.dev_workflows",
    ]
    assert sum(not workflow.dev_only for workflow in CATALOG) == 8


def test_catalog_categories_keep_ui_order() -> None:
    assert categories() == ["General", "Data model"]


def test_catalog_lookup_returns_workflow() -> None:
    workflow = by_id("documents.search")

    assert workflow.title == "Find documents"
    assert workflow.category == "General"


def test_catalog_output_columns_match_public_workflow_contract() -> None:
    expected = {
        "find.subject": [
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
        ],
        "find.organization": [
            "organization_id",
            "label",
            "fibo_classes",
            "jurisdictions",
            "registered_offices",
            "registration_numbers",
            "date_of_incorporation",
            "date_of_dissolution",
            "mentions",
            "mention_count",
            "edge_count",
        ],
        "find.person": [
            "person_id",
            "person",
            "date_of_birth",
            "nationality",
            "residence",
            "passport",
            "mention_count",
            "mentions",
        ],
        "documents.search": [
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
        ],
        "capital.shareholdings": [
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
        ],
        "governance.poa.register": [
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
        ],
        "events.timeline": [
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
        ],
        "data_model.guide": ["section"],
        "data_model.dev_workflows": ["section"],
    }

    assert {
        workflow.workflow_id: list(workflow.output_columns)
        for workflow in CATALOG
    } == expected
