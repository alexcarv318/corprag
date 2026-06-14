import re
from dataclasses import dataclass, field
from urllib.parse import urlencode

import chainlit as cl

CITATION_PATTERN = re.compile(r"\[\[cite:([^\]\s]+)\]\]")


@dataclass(frozen=True, slots=True)
class CitationRef:
    index: int
    file: str
    chunk_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class RenderedAnswer:
    text: str
    citations: list[CitationRef]


def render_citations(raw_text: str) -> RenderedAnswer:
    refs: dict[str, CitationRef] = {}

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        file_name, _, chunk_id = token.partition("#")
        key = file_name.strip()
        chunk_value = chunk_id.strip()
        if not key:
            return ""
        if key not in refs:
            refs[key] = CitationRef(index=len(refs) + 1, file=key)
        ref = refs[key]
        if chunk_value:
            ref.chunk_ids.add(chunk_value)
        query = urlencode({"file": key, "chunk": chunk_value})
        return f"[{ref.index}](#agent-source?{query})"

    text = CITATION_PATTERN.sub(replace, raw_text)
    return RenderedAnswer(text=text, citations=sorted(refs.values(), key=lambda ref: ref.index))


def citation_payload(citations: list[CitationRef]) -> list[dict[str, object]]:
    return [
        {
            "index": citation.index,
            "file": citation.file,
            "title": citation.file,
            "chunk_ids": sorted(citation.chunk_ids),
        }
        for citation in citations
    ]


async def finalize_message(final_message: cl.Message, raw_text: str) -> None:
    rendered = render_citations(raw_text)
    final_message.content = rendered.text
    if rendered.citations:
        final_message.actions = [
            cl.Action(
                name="show_sources",
                payload={"sources": citation_payload(rendered.citations)},
                label=f"Sources ({len(rendered.citations)})",
                tooltip="Open all sources",
                icon="book-open-text",
            )
        ]
    await final_message.send()  # type: ignore[no-untyped-call]
