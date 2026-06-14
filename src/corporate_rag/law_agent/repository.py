import re
from typing import Any

from corporate_rag.graph.interfaces import BaseGraphReader

DOMAIN_ALIASES: dict[str, str] = {
    "company": "corporate_law",
    "company_law": "corporate_law",
    "corporate": "corporate_law",
    "corporate law": "corporate_law",
}

JURISDICTION_ALIASES: dict[str, str] = {
    "ch": "CH",
    "che": "CH",
    "swiss": "CH",
    "switzerland": "CH",
}


def normalize_domain_key(domain: str) -> str:
    normalized = domain.strip().lower().replace("-", "_")
    return DOMAIN_ALIASES.get(normalized, normalized)


def normalize_jurisdiction_code(jurisdiction: str) -> str:
    normalized = jurisdiction.strip().lower().replace("-", "_")
    return JURISDICTION_ALIASES.get(normalized, jurisdiction.strip().upper())


def normalize_act_key(act_id: str) -> str:
    selector = act_id.strip()
    lowered = selector.lower()
    if lowered.startswith("ch-sr-"):
        return selector[6:].replace("-", ".")
    if lowered.startswith("sr "):
        return selector[3:].strip()
    return selector


def extract_public_article_number(article_id: str) -> str | None:
    selector = article_id.strip().lower()
    combined_suffix_match = re.search(r"(\d+)([a-z]{1,5})$", selector)
    if combined_suffix_match is not None:
        return f"{combined_suffix_match.group(1)}{combined_suffix_match.group(2)}"
    split_suffix_match = re.search(r"(\d+)-([a-z]{1,5})$", selector)
    if split_suffix_match is not None:
        return f"{split_suffix_match.group(1)}{split_suffix_match.group(2)}"
    numeric_match = re.search(r"(\d+)$", selector)
    if numeric_match is not None:
        return numeric_match.group(1)
    return None


def article_e_id_candidates(article_number: str) -> list[str]:
    compact = article_number.strip().lower()
    if not compact:
        return []
    digit_prefix_match = re.fullmatch(r"(\d+)([a-z]{1,5})", compact)
    if digit_prefix_match is None:
        return [f"art_{compact}"]
    digits = digit_prefix_match.group(1)
    suffix = digit_prefix_match.group(2)
    return [f"art_{digits}_{suffix}", f"art_{digits}{suffix}"]


def list_corpus_acts(
    client: BaseGraphReader,
    *,
    jurisdiction: str,
    domain: str,
) -> list[dict[str, Any]]:
    rows = client.read(
        """
        MATCH (:Jurisdiction {code: $jurisdiction_code})-[:HAS_ACT]->(act:Act)
              <-[:HAS_ACT]-(:LegalDomain {key: $domain_key})
        OPTIONAL MATCH (act)-[:HAS_EXPRESSION]->(expression:Expression)
        WITH act, expression
        ORDER BY expression.active_for_agent DESC, expression.applicability_date DESC
        WITH act, collect(expression)[0] AS expression
        RETURN act.key AS act_key,
               act.sr_number AS sr_number,
               act.title AS title,
               act.short_title AS short_title,
               expression.key AS expression_key,
               expression.language AS language
        ORDER BY act.sr_number ASC
        """.strip(),
        {
            "jurisdiction_code": normalize_jurisdiction_code(jurisdiction),
            "domain_key": normalize_domain_key(domain),
        },
    )
    return [_with_act_id(row) for row in rows]


def get_act_toc(client: BaseGraphReader, *, act_id: str) -> list[dict[str, Any]]:
    act_key = normalize_act_key(act_id)
    rows = client.read(
        """
        MATCH (act:Act {key: $act_key})-[:HAS_EXPRESSION]->
              (expression:Expression {active_for_agent: true})
        MATCH (expression)-[:CONTAINS_ARTICLE]->(article:Article)
        RETURN article.key AS article_key,
               article.number AS article_number,
               article.citation AS citation,
               article.heading AS heading,
               article.status AS status,
               article.sort_order AS sort_order
        ORDER BY sort_order ASC
        """.strip(),
        {"act_key": act_key},
    )
    return [_with_article_id(row, act_key=act_key) for row in rows]


def search_law(
    client: BaseGraphReader,
    *,
    query: str,
    jurisdiction: str,
    domain: str,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = [token.strip() for token in query.split() if token.strip()]
    if not tokens:
        return []
    return client.read(
        """
        CALL db.index.fulltext.queryNodes('law_paragraph_search', $query) YIELD node, score
        MATCH (article:Article)-[:HAS_PARAGRAPH]->(node)
        MATCH (expression:Expression)-[:CONTAINS_ARTICLE]->(article)
        MATCH (act:Act)-[:HAS_EXPRESSION]->(expression)
        MATCH (:Jurisdiction {code: $jurisdiction_code})-[:HAS_ACT]->(act)
              <-[:HAS_ACT]-(:LegalDomain {key: $domain_key})
        WHERE expression.active_for_agent = true
        RETURN node.key AS paragraph_key,
               article.key AS article_key,
               act.key AS act_key,
               act.sr_number AS sr_number,
               article.citation AS article_citation,
               node.citation AS paragraph_citation,
               article.heading AS heading,
               node.text AS text,
               score AS score
        ORDER BY score DESC
        LIMIT toInteger($limit)
        """.strip(),
        {
            "query": " ".join(tokens),
            "jurisdiction_code": normalize_jurisdiction_code(jurisdiction),
            "domain_key": normalize_domain_key(domain),
            "limit": limit,
        },
    )


def get_article(client: BaseGraphReader, *, article_id: str) -> dict[str, Any] | None:
    article_key = _resolve_article_key(client, article_id)
    if article_key is None:
        return None
    article_rows = client.read(
        """
        MATCH (expression:Expression)-[:CONTAINS_ARTICLE]->(article:Article {key: $article_key})
        MATCH (act:Act)-[:HAS_EXPRESSION]->(expression)
        RETURN article.key AS article_key,
               article.number AS number,
               article.citation AS citation,
               article.heading AS heading,
               article.intro_text AS intro_text,
               article.status AS status,
               act.key AS act_key,
               act.sr_number AS sr_number,
               act.title AS act_title,
               expression.language AS language
        """.strip(),
        {"article_key": article_key},
    )
    if not article_rows:
        return None
    article = article_rows[0]
    article["paragraphs"] = client.read(
        """
        MATCH (article:Article {key: $article_key})-[:HAS_PARAGRAPH]->(paragraph:Paragraph)
        RETURN paragraph.key AS paragraph_key,
               paragraph.number AS number,
               paragraph.citation AS citation,
               paragraph.term AS term,
               paragraph.text AS text,
               paragraph.sort_order AS sort_order
        ORDER BY paragraph.sort_order ASC
        """.strip(),
        {"article_key": article_key},
    )
    return article


def get_neighbor_articles(
    client: BaseGraphReader,
    *,
    article_id: str,
    window: int = 1,
) -> list[dict[str, Any]]:
    article_key = _resolve_article_key(client, article_id)
    if article_key is None:
        return []
    return client.read(
        """
        MATCH (expression:Expression)-[:CONTAINS_ARTICLE]->(article:Article {key: $article_key})
        MATCH (expression)-[:CONTAINS_ARTICLE]->(neighbor:Article)
        WHERE neighbor.sort_order >= article.sort_order - $window
          AND neighbor.sort_order <= article.sort_order + $window
        RETURN neighbor.key AS article_key,
               neighbor.number AS number,
               neighbor.citation AS citation,
               neighbor.heading AS heading,
               neighbor.status AS status,
               neighbor.sort_order AS sort_order
        ORDER BY neighbor.sort_order ASC
        """.strip(),
        {"article_key": article_key, "window": window},
    )


def get_article_citations(
    client: BaseGraphReader,
    *,
    article_id: str,
) -> list[dict[str, Any]]:
    article_key = _resolve_article_key(client, article_id)
    if article_key is None:
        return []
    return client.read(
        """
        MATCH (:Article {key: $article_key})-[:HAS_PARAGRAPH]->(paragraph:Paragraph)
              -[citation:CITES]->(target)
        RETURN paragraph.key AS paragraph_key,
               citation.raw_text AS raw_text,
               citation.citation_type AS citation_type,
               target.key AS target_key,
               labels(target) AS target_labels
        ORDER BY paragraph.sort_order ASC, citation.raw_text ASC
        """.strip(),
        {"article_key": article_key},
    )


def _resolve_article_key(client: BaseGraphReader, article_id: str) -> str | None:
    selector = article_id.strip()
    if selector.startswith("ch-sr-"):
        rows = client.read(
            "MATCH (article:Article {key: $article_key}) RETURN article.key AS article_key",
            {"article_key": selector},
        )
        return str(rows[0]["article_key"]) if rows else None
    public_number = extract_public_article_number(selector)
    if public_number is None:
        return None
    for candidate in article_e_id_candidates(public_number):
        rows = client.read(
            """
            MATCH (article:Article)
            WHERE article.key ENDS WITH $candidate
            RETURN article.key AS article_key
            ORDER BY size(article.key) ASC
            LIMIT 1
            """.strip(),
            {"candidate": candidate},
        )
        if rows:
            return str(rows[0]["article_key"])
    return None


def _with_act_id(row: dict[str, Any]) -> dict[str, Any]:
    act_key = str(row.get("act_key") or "")
    return {**row, "act_id": f"ch-sr-{act_key.replace('.', '-')}" if act_key else None}


def _with_article_id(row: dict[str, Any], *, act_key: str) -> dict[str, Any]:
    return {
        **row,
        "article_id": f"ch-sr-{act_key.replace('.', '-')}-{row.get('article_number', '')}",
    }
