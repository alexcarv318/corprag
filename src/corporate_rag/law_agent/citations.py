import re

import chainlit as cl


def sanitize_answer(raw_text: str) -> str:
    paragraphs = re.split(r"\n{2,}", raw_text.strip())
    public_paragraphs = [
        paragraph for paragraph in paragraphs if not _contains_internal_metadata(paragraph)
    ]
    return "\n\n".join(public_paragraphs).strip()


async def finalize_message(final_message: cl.Message, raw_text: str) -> None:
    final_message.content = sanitize_answer(raw_text)
    await final_message.send()  # type: ignore[no-untyped-call]


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
