import re
from typing import Any

FEDLEX_PUBLIC_BASE_BY_SR: dict[str, str] = {
    "220": "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/it",
    "221.301": "https://www.fedlex.admin.ch/eli/cc/2004/320/it",
    "221.411": "https://www.fedlex.admin.ch/eli/cc/2007/686/it",
    "235.1": "https://www.fedlex.admin.ch/eli/cc/2022/491/it",
    "281.1": "https://www.fedlex.admin.ch/eli/cc/11/529_488_529/it",
    "291": "https://www.fedlex.admin.ch/eli/cc/1988/1776_1776_1776/it",
    "641.10": "https://www.fedlex.admin.ch/eli/cc/1974/11_11_11/it",
    "642.11": "https://www.fedlex.admin.ch/eli/cc/1991/1184_1184_1184/it",
    "642.14": "https://www.fedlex.admin.ch/eli/cc/1991/1256_1256_1256/it",
}

LAW_CITATION_PATTERN = re.compile(
    r"(?P<tick>`?)"
    r"(?P<citation>"
    r"SR\s+(?P<sr>\d+(?:\.\d+)*)\s+"
    r"Art\.\s+(?P<article>\d+[A-Za-z]{0,6})"
    r"(?P<tail>"
    r"(?:\s+(?:para\.|paras\.|let\.|lets\.|no\.|nos\.)\s+"
    r"[0-9A-Za-z]+(?:\s*(?:,|and|or|-)\s*[0-9A-Za-z]+)*)*"
    r")"
    r")"
    r"(?P=tick)"
)


def sanitize_answer(raw_text: str) -> str:
    paragraphs = re.split(r"\n{2,}", raw_text.strip())
    public_paragraphs = [
        paragraph for paragraph in paragraphs if not _contains_internal_metadata(paragraph)
    ]
    return "\n\n".join(public_paragraphs).strip()


async def finalize_message(final_message: Any, raw_text: str) -> None:
    final_message.content = link_law_citations(sanitize_answer(raw_text))
    await final_message.send()  # type: ignore[no-untyped-call]


def link_law_citations(raw_text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if _already_markdown_linked(raw_text, match.start()):
            return match.group(0)

        sr_number = match.group("sr")
        article_number = normalize_article_number(match.group("article"))
        url = fedlex_article_url(sr_number, article_number)
        if url is None:
            return match.group(0)

        label = match.group("citation").strip()
        if match.group("tick"):
            return f"[`{label}`]({url})"
        return f"[{label}]({url})"

    return LAW_CITATION_PATTERN.sub(replace, raw_text)


def fedlex_article_url(sr_number: str, article_number: str) -> str | None:
    base_url = FEDLEX_PUBLIC_BASE_BY_SR.get(sr_number)
    if base_url is None:
        return None
    return f"{base_url}#{article_anchor(article_number)}"


def article_anchor(article_number: str) -> str:
    normalized = normalize_article_number(article_number)
    letter_suffix = re.fullmatch(r"(\d+)([a-z]+)", normalized)
    if letter_suffix is None:
        return f"art_{normalized}"
    return f"art_{letter_suffix.group(1)}_{letter_suffix.group(2)}"


def normalize_article_number(article_number: str) -> str:
    return article_number.strip().replace(" ", "").lower()


def _contains_internal_metadata(paragraph: str) -> bool:
    normalized = paragraph.lower()
    if re.search(r"`?\d+(?:\.\d+)*:[a-z]{2}:[a-z0-9_./:-]+`?", paragraph):
        return True

    internal_terms = (
        "active expression",
        "expression metadata",
        "authoritative-looking",
        "law graph",
        "neo4j",
        "mcp",
        "internal id",
        "manifestation",
        "graph node",
    )
    return any(term in normalized for term in internal_terms)


def _already_markdown_linked(text: str, start_index: int) -> bool:
    return start_index > 0 and text[start_index - 1] == "["
