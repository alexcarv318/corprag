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

## Run backend

```bash
docker compose -f docker-compose.yml up --build
```

## Run frontend

```bash
make dev-web
```

Health check:

```bash
curl http://127.0.0.1:8088/health
```

Access frontend at http://127.0.0.1:5173/

## Checks

```bash
uv run ruff check .
uv run mypy
uv run pytest
```

