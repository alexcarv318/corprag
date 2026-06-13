# Corporate RAG

Monolithic rewrite of the Corporate NER pilot.

The first slice only provides the backend application shell:

- FastAPI app factory.
- `/health` endpoint.
- Typer CLI entrypoint.
- Pydantic settings.
- Workflow API shell.

## Setup

```bash
uv sync --extra dev
```

## Run

```bash
uv run corporate-rag serve --host 127.0.0.1 --port 8088
```

Health check:

```bash
curl http://127.0.0.1:8088/health
```

## Checks

```bash
uv run ruff check .
uv run mypy
uv run pytest
```

