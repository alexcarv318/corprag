from mcp.server.fastmcp import FastMCP

from corporate_rag.law_agent import repository
from corporate_rag.law_agent.agent import _graph_client


def build_server(*, host: str = "127.0.0.1", port: int = 18801) -> FastMCP:
    graph = _graph_client()
    server = FastMCP(
        name="corporate-rag-law-agent",
        host=host,
        port=port,
        json_response=True,
        stateless_http=True,
    )

    @server.tool(name="list_corpus_acts")
    def list_corpus_acts_tool(jurisdiction: str, domain: str) -> list[dict[str, object]]:
        return repository.list_corpus_acts(graph, jurisdiction=jurisdiction, domain=domain)

    @server.tool(name="get_act_toc")
    def get_act_toc_tool(act_id: str) -> list[dict[str, object]]:
        return repository.get_act_toc(graph, act_id=act_id)

    @server.tool(name="search_law")
    def search_law_tool(
        query: str,
        jurisdiction: str,
        domain: str,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        return repository.search_law(
            graph,
            query=query,
            jurisdiction=jurisdiction,
            domain=domain,
            limit=limit,
        )

    @server.tool(name="get_article")
    def get_article_tool(article_id: str) -> dict[str, object] | None:
        return repository.get_article(graph, article_id=article_id)

    @server.tool(name="get_neighbor_articles")
    def get_neighbor_articles_tool(
        article_id: str,
        window: int = 1,
    ) -> list[dict[str, object]]:
        return repository.get_neighbor_articles(graph, article_id=article_id, window=window)

    @server.tool(name="get_article_citations")
    def get_article_citations_tool(article_id: str) -> list[dict[str, object]]:
        return repository.get_article_citations(graph, article_id=article_id)

    return server


def main(
    host: str = "127.0.0.1",
    port: int = 18801,
    transport: str = "streamable-http",
) -> None:
    server = build_server(host=host, port=port)
    if transport == "stdio":
        server.run(transport="stdio")
        return
    server.run(transport="streamable-http")
