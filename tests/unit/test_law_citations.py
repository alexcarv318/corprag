from corporate_rag.law_agent.citations import (
    article_anchor,
    link_law_citations,
    normalize_article_number,
    sanitize_answer,
)


def test_link_law_citations_links_backticked_sr_article_to_fedlex_anchor() -> None:
    linked = link_law_citations("See `SR 220 Art. 11` for the rule.")

    assert linked == (
        "See [`SR 220 Art. 11`](https://www.fedlex.admin.ch/eli/cc/27/317_321_377/it#art_11) "
        "for the rule."
    )


def test_link_law_citations_preserves_paragraph_suffix_in_label() -> None:
    linked = link_law_citations("The form rule is SR 220 Art. 14 para. 2bis.")

    assert linked == (
        "The form rule is "
        "[SR 220 Art. 14 para. 2bis](https://www.fedlex.admin.ch/eli/cc/27/317_321_377/it#art_14)."
    )


def test_link_law_citations_uses_letter_article_anchor() -> None:
    linked = link_law_citations("The cooling-off rule is `SR 220 Art. 40a`.")

    assert linked == (
        "The cooling-off rule is "
        "[`SR 220 Art. 40a`](https://www.fedlex.admin.ch/eli/cc/27/317_321_377/it#art_40_a)."
    )


def test_link_law_citations_leaves_unknown_sr_number_unchanged() -> None:
    text = "Missing corpus citation: `SR 999.999 Art. 1`."

    assert link_law_citations(text) == text


def test_link_law_citations_does_not_wrap_existing_markdown_link() -> None:
    text = "[SR 220 Art. 620](https://example.test/source)"

    assert link_law_citations(text) == text


def test_sanitize_answer_removes_internal_expression_metadata() -> None:
    answer = (
        "The legal answer is grounded in SR 220 Art. 620.\n\n"
        "The corpus contains an active Italian expression of the Code of Obligations "
        "(`220:it:unknown`). I have relied on that authoritative-looking active expression."
    )

    assert sanitize_answer(answer) == "The legal answer is grounded in SR 220 Art. 620."


def test_article_anchor_normalization_matches_fedlex_article_anchors() -> None:
    assert article_anchor("40A") == "art_40_a"
    assert normalize_article_number("40A") == "40a"
