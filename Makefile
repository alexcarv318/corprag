.PHONY: lint typecheck test coverage dev-backend dev-web

lint:
	uv run --extra dev ruff check .

typecheck:
	uv run --extra dev mypy --strict src tests

test:
	uv run --extra dev pytest

coverage:
	uv run --extra dev pytest --cov --cov-report=term-missing

dev-backend:
	uv run corporate-rag serve --host 127.0.0.1 --port 8088

dev-web:
	cd apps/web && npm run dev
