import pytest

from corporate_rag.facets.repository import facetable_pairs, get_facet
from corporate_rag.typeahead.repository import (
    context_clause_for_kind,
    typeahead_cypher_for_kind,
)
from corporate_rag.workflows import repository as workflow_repository

WORKFLOW_QUERY_NAMES = (
    "SUBJECT_OVERVIEW",
    "ORGANIZATION_OVERVIEW",
    "PERSON_OVERVIEW",
    "DOCUMENTS_SEARCH",
    "CAPITAL_EVENTS",
    "POA_REGISTER",
    "EVENTS_TIMELINE",
    "SUBJECT_IDENTIFIERS",
    "SUBJECT_BOARD_HISTORY",
    "PERSON_ROLES",
    "PERSON_AUTHORITY",
    "ORGANIZATION_IDENTIFIERS",
    "ORGANIZATION_OFFICES",
    "CAPITAL_HOLDERS",
)


def test_typeahead_query_layer_builds_subject_search_query() -> None:
    query = typeahead_cypher_for_kind("subject", has_query=True)

    assert "subject_search" in query
    assert "RETURN n.subjectId AS id" in query


def test_typeahead_query_layer_builds_context_filtered_person_query() -> None:
    query = typeahead_cypher_for_kind(
        "person",
        has_query=False,
        context={"subject_id": "subject-aeh"},
    )

    assert "MATCH (n:Entity:Person)" in query
    assert "$context_subject_id" in query


def test_typeahead_context_clause_ignores_subject_kind() -> None:
    assert context_clause_for_kind("subject", {"subject_id": "subject-aeh"}) == ""


def test_facet_query_layer_lists_supported_pairs() -> None:
    assert facetable_pairs() == [
        ("documents.search", "doc_type"),
        ("events.timeline", "event_type"),
    ]


def test_facet_query_layer_resolves_documents_doc_type_query() -> None:
    facet = get_facet("documents.search", "doc_type")

    assert "MATCH (w:Work)-[:HAS_REALIZATION]->(expr:Expression)" in facet.cypher
    assert "include_cancelled" in facet.parameters


def test_facet_query_layer_rejects_unknown_pair() -> None:
    with pytest.raises(KeyError):
        get_facet("find.subject", "missing")


def test_workflow_repository_queries_are_readable_multiline_strings() -> None:
    for query_name in WORKFLOW_QUERY_NAMES:
        query = getattr(workflow_repository, query_name)

        assert "\n" in query
        assert "\\n" not in query
        assert query == query.strip()
