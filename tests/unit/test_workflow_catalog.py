from corporate_rag.workflows.catalog import CATALOG, by_id, categories


def test_ui_catalog_contains_only_current_v2_surface() -> None:
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
