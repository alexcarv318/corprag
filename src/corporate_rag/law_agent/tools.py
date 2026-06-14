from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from corporate_rag.agents.tool_output import normalize_tool_outputs
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.law_agent import repository


def build_langchain_tools(graph: BaseGraphReader) -> list[BaseTool]:
    async def list_corpus_acts(jurisdiction: str, domain: str) -> list[dict[str, Any]]:
        return repository.list_corpus_acts(graph, jurisdiction=jurisdiction, domain=domain)

    async def get_act_toc(act_id: str) -> list[dict[str, Any]]:
        return repository.get_act_toc(graph, act_id=act_id)

    async def search_law(
        query: str,
        jurisdiction: str,
        domain: str,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        return repository.search_law(
            graph,
            query=query,
            jurisdiction=jurisdiction,
            domain=domain,
            limit=limit,
        )

    async def get_article(article_id: str) -> dict[str, Any] | None:
        return repository.get_article(graph, article_id=article_id)

    async def get_neighbor_articles(
        article_id: str,
        window: int = 1,
    ) -> list[dict[str, Any]]:
        return repository.get_neighbor_articles(graph, article_id=article_id, window=window)

    async def get_article_citations(article_id: str) -> list[dict[str, Any]]:
        return repository.get_article_citations(graph, article_id=article_id)

    tools = [
        StructuredTool.from_function(
            coroutine=list_corpus_acts,
            name="list_corpus_acts",
            description="List acts available for a jurisdiction and legal domain pair.",
        ),
        StructuredTool.from_function(
            coroutine=get_act_toc,
            name="get_act_toc",
            description="Return the ordered article table of contents for one act.",
        ),
        StructuredTool.from_function(
            coroutine=search_law,
            name="search_law",
            description="Full-text search over law paragraphs for a jurisdiction and domain.",
        ),
        StructuredTool.from_function(
            coroutine=get_article,
            name="get_article",
            description="Read one article with paragraphs before making a final legal answer.",
        ),
        StructuredTool.from_function(
            coroutine=get_neighbor_articles,
            name="get_neighbor_articles",
            description="Read adjacent articles in the same act expression.",
        ),
        StructuredTool.from_function(
            coroutine=get_article_citations,
            name="get_article_citations",
            description="Read citation edges from one article's paragraphs.",
        ),
    ]
    return normalize_tool_outputs(tools)
