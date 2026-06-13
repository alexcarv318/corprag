import re
from typing import Any

from corporate_rag.graph.interfaces import BaseGraphReader


def resolve_value_evidence(
    client: BaseGraphReader,
    *,
    value: str,
    column: str,
    files: list[str],
    entity_id: str | None = None,
    context: str | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    cleaned_value = value.strip()
    terms = build_terms(column, cleaned_value)
    empty_payload: dict[str, Any] = {
        "value": cleaned_value,
        "column": column,
        "highlight_terms": terms,
        "chunks": [],
    }
    cleaned_files = [file.strip() for file in files if file.strip()]
    cleaned_entity_id = (entity_id or "").strip()
    if not terms or (not cleaned_files and not cleaned_entity_id):
        return empty_payload

    rows = client.read(
        EVIDENCE_CYPHER,
        {
            "files": cleaned_files,
            "entity_id": cleaned_entity_id,
            "terms": terms,
        },
    )
    context_token = (context or "").strip().lower()
    ranked_rows = sorted(
        ({**row, "_rank": rank_chunk(row, terms, context_token)} for row in rows),
        key=lambda row: row["_rank"],
    )

    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in ranked_rows:
        chunk_id = str(row.get("chunk_id") or "")
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        text = str(row.get("text") or "")
        chunks.append(
            {
                "file": row.get("file") or "",
                "chunk_id": chunk_id,
                "text": text,
                "snippet": snippet(text, terms),
            }
        )
        if len(chunks) >= limit:
            break

    return {
        "value": cleaned_value,
        "column": column,
        "highlight_terms": terms,
        "chunks": chunks,
    }


def classify_column(column: str) -> str:
    name = column.strip().lower()
    if name in DATE_COLUMN_NAMES:
        return "date"
    if name in NUMBER_COLUMN_NAMES:
        return "number"
    if name.startswith("date_") or "valid_" in name:
        return "date"
    if name.endswith(DATE_COLUMN_SUFFIXES):
        return "date"
    return "text"


def build_terms(column: str, value: str) -> list[str]:
    strategy = classify_column(column)
    if strategy == "date":
        return dedupe(date_terms(value))
    if strategy == "number":
        return dedupe(number_terms(value))
    return text_terms(value)


def date_terms(value: str) -> list[str]:
    match = ISO_DATE_RE.match(value.strip())
    if match is None:
        return text_terms(value)

    year, month, day = (int(part) for part in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return [value]

    month_name = MONTHS_EN[month - 1]
    month_abbr = month_name[:3]
    return [
        f"{day} {month_name} {year}",
        f"{day} {month_abbr} {year}",
        f"{month_name} {day}, {year}",
        f"{month_abbr} {day}, {year}",
        f"{month_name} {day} {year}",
        f"{day:02d}.{month:02d}.{year}",
        f"{day}.{month}.{year}",
        f"{day:02d}/{month:02d}/{year}",
        f"{month:02d}/{day:02d}/{year}",
        f"{day:02d}-{month:02d}-{year}",
        f"{year}-{month:02d}-{day:02d}",
    ]


def number_terms(value: str) -> list[str]:
    integer_part = re.split(r"[.,]", value.strip(), maxsplit=1)[0]
    digits = re.sub(r"[^0-9]", "", integer_part)
    if not digits:
        return text_terms(value)

    return [
        digits,
        group_digits(digits, ","),
        group_digits(digits, "."),
        group_digits(digits, "'"),
        group_digits(digits, " "),
    ]


def group_digits(digits: str, separator: str) -> str:
    reversed_digits = digits[::-1]
    chunks = [reversed_digits[index : index + 3] for index in range(0, len(digits), 3)]
    return separator.join(chunks)[::-1]


def text_terms(value: str) -> list[str]:
    text = value.strip()
    if not text:
        return []

    terms = [text]
    head = text.split(",", 1)[0].strip()
    if head and head != text and len(head) >= 5:
        terms.append(head)
    return dedupe([term for term in terms if len(term) >= 3])


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def rank_chunk(
    row: dict[str, Any],
    terms: list[str],
    context_token: str,
) -> tuple[int, int, int]:
    text = str(row.get("text") or "").lower()
    matched = sum(1 for term in terms if term.lower() in text)
    context_hit = 1 if context_token and context_token in text else 0
    return (-matched, -context_hit, len(text))


def snippet(text: str, terms: list[str], window: int = 160) -> str:
    lowered = text.lower()
    best = -1
    for term in terms:
        index = lowered.find(term.lower())
        if index != -1 and (best == -1 or index < best):
            best = index

    if best == -1:
        return text[:window].strip()

    start = max(0, best - window // 2)
    end = min(len(text), best + window // 2)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


MONTHS_EN: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

DATE_COLUMN_NAMES: frozenset[str] = frozenset(
    {
        "date_of_incorporation",
        "date_of_dissolution",
        "date_of_birth",
        "effective_date",
        "as_of",
        "term_start",
        "term_end",
        "from",
        "to",
        "valid_from",
        "valid_to",
        "valid_until",
        "active_from",
        "active_until",
        "phase_valid_from",
        "phase_valid_to",
        "latest_certificate_date",
        "latest_good_standing_date",
    }
)
DATE_COLUMN_SUFFIXES: tuple[str, ...] = (
    "_valid_from",
    "_valid_to",
    "_valid_until",
    "_from",
    "_to",
    "_until",
    "_date",
)
NUMBER_COLUMN_NAMES: frozenset[str] = frozenset(
    {
        "amount",
        "shares",
        "share_count",
        "number_of_shares",
        "total_shares",
        "nominal_value",
        "share_capital",
        "capital",
    }
)
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

EVIDENCE_CYPHER = """
CALL {
  UNWIND $files AS f
  MATCH (item:Item)
  WHERE item.inbox_filename = f OR item.item_id = f
  MATCH (item)<-[:HAS_EXEMPLAR]-(:Manifestation)
        <-[:HAS_EMBODIMENT]-(:Expression)-[:HAS_PART]->(c:Chunk)
  RETURN c
  UNION
  MATCH (c:Chunk)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(e)
  WHERE $entity_id IS NOT NULL AND $entity_id <> ''
    AND (e.entityId = $entity_id OR e.subjectId = $entity_id)
  RETURN c
}
WITH DISTINCT c AS chunk
WHERE chunk.text IS NOT NULL
  AND any(term IN $terms WHERE toLower(chunk.text) CONTAINS toLower(term))
OPTIONAL MATCH (chunk)<-[:HAS_PART]-(:Expression)
              -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
RETURN DISTINCT coalesce(item.inbox_filename, item.item_id, '') AS file,
       chunk.chunk_id AS chunk_id,
       chunk.text AS text
LIMIT 200
""".strip()
