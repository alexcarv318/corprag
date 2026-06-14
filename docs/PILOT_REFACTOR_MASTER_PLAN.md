# Corporate RAG Pilot Refactor Master Plan

Status: execution plan for rebuilding the pilot into a clean monolithic product in `corporate-rag`.

Implementation progress as of 2026-06-12:

- Backend application shell is in place.
- Neo4j settings/client foundation is in place.
- Workflow domain models, execution engine, public serializers, and API shell are migrated.
- UI backend workflow catalog is migrated from the current v2 surface: 8 public UI workflows plus the dev-only data-model workflow.
- UI workflow query dependencies and authority registry helpers are migrated for the workflow backend slice.
- Multi-table workflow execution is migrated for `find.subject`, focused `find.person`, focused `find.organization`, and `capital.shareholdings`.
- FastAPI app factory wires the default workflow engine to the migrated catalog.
- Current green check: `ruff`, `mypy --strict`, and `pytest` pass.

Source project: `../corporate-ner`  
Target project: `../corporate-rag`

## 1. Goal

Build a clean monolith that preserves the useful pilot behavior and removes obsolete experimental code.

The target product must contain:

- Corporate graph workflows UI and API.
- Internal corporate archive agent.
- Swiss law agent.
- Corporate graph MCP server for agent tools.
- Swiss law MCP server.
- Corporate document ingestion foundation.
- Swiss law ingestion.
- Neo4j access, schema/bootstrap, backups, and deployment tooling.
- Production AWS infrastructure for 50-100 users.

The target product must not carry forward:

- OpenClaw/Argus loop concepts that are no longer used.
- One-off remediation scripts unless they are converted into documented migrations.
- Old workflow versions exposed as primary public surfaces.
- Runtime artifacts, reports, scratch directories, generated dumps, and local state.
- Duplicate compatibility wrappers that only preserve old import paths.

## 2. Current State Inventory

Useful source areas in `corporate-ner`:

```text
corporate-ner/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── infra/systemd/corpner-workflows.service
├── public/
│   ├── corprag.css
│   ├── corprag.js
│   ├── favicon.svg
│   └── theme.json
├── docs/internal/
│   ├── 2026-05-12_workflows.html
│   ├── 2026-05-12_workflows_catalog.md
│   ├── 2026-05-15_DEPLOY.md
│   └── 2026-05-20_corpner-agent-mcp-tools.md
├── src/corporate_ner/
│   ├── agent_mcp/
│   ├── chat/
│   ├── distributed/
│   ├── graph_mcp/
│   ├── graph_tools/
│   ├── load/
│   └── workflows/
├── swiss/
│   └── law/
└── tests/
```

Primary runtime today:

- `corpner-workflows serve` starts FastAPI/Uvicorn.
- `/` and `/v2` serve `docs/internal/2026-05-12_workflows.html`.
- `/api/*` serves workflow catalog, typeahead, facets, evidence, document source, and workflow execution.
- `/agent` mounts Chainlit through `chainlit.utils.mount_chainlit`.
- Chainlit has two modes: internal corporate agent and Swiss law agent.
- Internal agent uses LangChain, DeepAgents, and `corpner-agent-mcp`.
- Law agent uses LangChain, DeepAgents, and `corpner-law-mcp`.
- Corporate graph uses Neo4j database `neo4j`.
- Law graph uses Neo4j database `law`.
- Deployment currently uses `src/corporate_ner/distributed` and EC2/systemd.

Important source modules:

```text
src/corporate_ner/workflows/
├── asgi.py                 # unified FastAPI app, Chainlit mount, API routes
├── cli.py                  # corpner-workflows CLI
├── engine.py               # WorkflowEngine
├── models.py               # Workflow, Parameter, WorkflowResult
├── typeahead.py
├── evidence.py
├── document_source.py
├── catalog.py              # broad v1 catalog
├── v2/catalog.py           # current narrow client-facing catalog
├── v2/facets.py
└── queries/                # Cypher workflow definitions

src/corporate_ner/agent_mcp/
├── server.py               # FastMCP server, read-only corporate tool surface
├── handlers.py
├── schemas.py              # Pydantic tool inputs
├── tool_registry.py        # generated workflow tool specs
├── workflow_catalog.py
└── retrieval/

src/corporate_ner/chat/
├── chat_app.py             # Chainlit app for internal + law mode
├── agent_factory.py        # internal DeepAgent builder
├── prompts.py
├── persistence.py
├── sources.py
├── signup_page.py
├── ui.py
└── config.py

src/corporate_ner/load/
├── pipeline.py             # normalize -> render -> ocr -> vision -> chunk -> embed -> summarize -> persist
├── normalize.py
├── render.py
├── vision.py
├── chunker.py
├── embed.py
├── summarize.py
├── persist.py
└── types.py

swiss/law/
├── agent/
├── graph/
├── ingestion/
└── mcp/

src/corporate_ner/distributed/
├── cli.py
├── config.py
├── services_ec2.py
├── ec2.py
├── bootstrap.py
└── neo4j/
```

Current target `corporate-rag` is essentially empty:

```text
corporate-rag/
├── .python-version
├── pyproject.toml
└── corporate-ner.code-workspace
```

## 3. Non-Negotiable Refactor Rules

1. Preserve working behavior before deleting old code.
2. Migrate one vertical slice at a time.
3. Every migrated surface gets tests before the next surface starts.
4. Public backend contracts use strict types.
5. Pydantic is used at external boundaries: API requests/responses, MCP tools, settings, ingestion manifests.
6. Internal passive data can use dataclasses or TypedDicts when no validation is needed.
7. Backend must pass `mypy --strict`.
8. Frontend uses JavaScript, not TypeScript.
9. No old import compatibility shims.
10. No `from __future__ import annotations`.
11. No non-empty `__init__.py`.
12. No hidden global runtime clients in business logic.
13. Neo4j access goes through explicit repositories/clients.
14. Agent tools remain read-only unless a future admin graph mutation surface is explicitly designed.
15. Ingestion is architected now, but full corporate ingestion quality is not a phase-1 implementation target.
16. Local Neo4j configuration must track the existing production/pilot Neo4j Enterprise line, plugins, databases, import paths, and MCP support services.
17. Product code and tests in `corporate-rag` must read as a first-class product implementation, not as a compatibility layer or numbered remake. Historical source-project labels such as old version names, migration-only module names, parity wrappers, and pilot/legacy wording belong only in migration planning notes, not in runtime modules, public API text, or test names.

## 4. Target Architecture

One repository. One product. Clear internal modules.

Runtime shape:

```text
Browser
  ├── React workflows app: /, /workflows
  └── Chainlit agent app: /agent

FastAPI backend
  ├── Serves React static build in production
  ├── Provides /api/*
  ├── Mounts Chainlit at /agent
  ├── Starts internal MCP servers through stdio for local single-process development
  └── Calls private HTTP MCP services in compose/AWS deployments

Neo4j
  ├── database: neo4j
  └── database: law
```

Keep the current database names (`neo4j` and `law`) during migration. Rename
`neo4j` to `corporate` only after backup/restore rehearsal and an explicit data
migration plan.

Recommended backend stack:

- Python 3.12.
- `uv`.
- FastAPI + Uvicorn.
- Neo4j Python driver.
- Pydantic v2 for settings, API, MCP schemas.
- Typer for CLI.
- Chainlit for chat UI.
- LangChain + DeepAgents for agents.
- FastMCP for MCP servers.
- Pytest, pytest-asyncio where needed.
- Ruff for lint/format.
- Mypy strict.

Recommended frontend stack:

- Vite.
- React.
- JavaScript.
- CSS modules or plain CSS.
- No TypeScript in phase 1.
- No heavyweight state manager.
- Fetch-based API client.
- Component tests only after the UI stabilizes; first priority is backend contract tests and Playwright smoke tests.

Recommended infrastructure stack:

- AWS CDK in Python, unless Terraform is already preferred by the deployment operator.
- ECS Fargate for the app container.
- ALB with HTTPS.
- CloudFront in front of ALB if global latency/static caching matters.
- S3 for document upload staging, backups, deployment artifacts.
- Secrets Manager for API keys and Neo4j credentials.
- CloudWatch logs and alarms.
- Neo4j deployment decision:
  - Preferred production: Neo4j Aura Professional/Enterprise if client data policy allows.
  - Controlled AWS production: Neo4j Enterprise on EC2 with EBS gp3, S3 backups, SSM, automated snapshots.
  - Avoid running Neo4j inside Fargate for production.

## 5. Target Repository Tree

```text
corporate-rag/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── data_model.md
│   ├── ingestion.md
│   ├── workflows.md
│   ├── agents.md
│   ├── operations.md
│   └── adr/
│       ├── 0001-monolith.md
│       ├── 0002-react-workflows-ui.md
│       ├── 0003-chainlit-agent-surface.md
│       ├── 0004-neo4j-production-shape.md
│       └── 0005-ingestion-boundaries.md
├── apps/
│   └── web/
│       ├── package.json
│       ├── vite.config.js
│       ├── index.html
│       ├── public/
│       └── src/
│           ├── main.jsx
│           ├── App.jsx
│           ├── api/
│           ├── components/
│           ├── features/
│           ├── styles/
│           └── utils/
├── src/
│   └── corporate_rag/
│       ├── __init__.py
│       ├── cli.py
│       ├── settings.py
│       ├── app/
│       ├── graph/
│       ├── workflows/
│       ├── agents/
│       ├── mcp/
│       ├── ingestion/
│       ├── law/
│       ├── documents/
│       ├── auth/
│       ├── storage/
│       └── observability/
├── infra/
│   ├── README.md
│   ├── cdk.json
│   ├── app.py
│   ├── corporate_rag_infra/
│   └── scripts/
├── scripts/
│   ├── dev.sh
│   ├── smoke_local.py
│   ├── export_current_contracts.py
│   └── compare_workflow_outputs.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   └── data/
└── tools/
    └── migration/
```

## 6. Target Backend Tree

```text
src/corporate_rag/
├── __init__.py
├── cli.py
├── settings.py
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI factory
│   ├── lifespan.py
│   ├── static.py
│   └── health.py
├── auth/
│   ├── __init__.py
│   ├── models.py
│   ├── password_auth.py
│   ├── repository.py
│   └── router.py
├── graph/
│   ├── __init__.py
│   ├── neo4j_client.py
│   ├── settings.py
│   ├── schema.py
│   └── transactions.py
├── workflows/
│   ├── __init__.py
│   ├── router.py
│   ├── catalog.py
│   ├── engine.py
│   ├── models.py
│   ├── repository.py             # workflow Cypher templates and graph reads
│   └── serializers.py
├── typeahead/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── router.py
├── facets/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── router.py
├── evidence/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── router.py
├── agents/
│   ├── __init__.py
│   ├── chainlit_app.py
│   ├── settings.py
│   ├── persistence.py
│   ├── modes.py
│   ├── citations.py
│   ├── ui.py
│   ├── internal/
│   │   ├── __init__.py
│   │   ├── factory.py
│   │   ├── prompts.py
│   │   ├── sources.py
│   │   └── tools.py
│   └── law/
│       ├── __init__.py
│       ├── factory.py
│       ├── prompts.py
│       └── citations.py
├── mcp/
│   ├── __init__.py
│   ├── runner.py
│   ├── corporate/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── handlers.py
│   │   ├── schemas.py
│   │   ├── tool_registry.py
│   │   └── retrieval/
│   └── law/
│       ├── __init__.py
│       ├── server.py
│       ├── handlers.py
│       ├── schemas.py
│       └── identifiers.py
├── ingestion/
│   ├── __init__.py
│   ├── router.py
│   ├── models.py
│   ├── service.py
│   ├── corporate/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── normalize.py
│   │   ├── render.py
│   │   ├── ocr.py
│   │   ├── vision.py
│   │   ├── chunker.py
│   │   ├── embed.py
│   │   ├── summarize.py
│   │   ├── persist.py
│   │   ├── extraction.py
│   │   └── resolution.py
│   └── law/
│       ├── __init__.py
│       ├── akn_parser.py
│       ├── manifest.py
│       ├── service.py
│       ├── writer.py
│       └── embeddings.py
├── law/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   ├── schema.py
│   └── corpus/
│       └── swiss_corporate_law.json
├── documents/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── router.py
├── storage/
│   ├── __init__.py
│   ├── local.py
│   └── s3.py
└── observability/
    ├── __init__.py
    ├── logging.py
    ├── metrics.py
    └── errors.py
```

## 7. Target Frontend Tree

```text
apps/web/
├── package.json
├── vite.config.js
├── index.html
├── public/
│   ├── favicon.svg
│   └── brand/
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── api/
│   │   ├── client.js
│   │   ├── workflows.js
│   │   ├── documents.js
│   │   └── auth.js
│   ├── components/
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── Modal.jsx
│   │   ├── Table.jsx
│   │   ├── Tabs.jsx
│   │   └── Toast.jsx
│   ├── features/
│   │   ├── shell/
│   │   │   ├── Layout.jsx
│   │   │   ├── Navigation.jsx
│   │   │   └── Disclaimer.jsx
│   │   ├── workflows/
│   │   │   ├── WorkflowCatalog.jsx
│   │   │   ├── WorkflowForm.jsx
│   │   │   ├── WorkflowResults.jsx
│   │   │   ├── FacetSelect.jsx
│   │   │   ├── TypeaheadInput.jsx
│   │   │   └── EvidenceDrawer.jsx
│   │   ├── documents/
│   │   │   ├── DocumentSourceDrawer.jsx
│   │   │   └── DocumentTitle.jsx
│   │   └── agent/
│   │       └── AgentLink.jsx
│   ├── styles/
│   │   ├── base.css
│   │   ├── theme.css
│   │   └── workflows.css
│   └── utils/
│       ├── format.js
│       └── queryString.js
└── tests/
    └── smoke.spec.js
```

Frontend rule: first migrate the existing HTML behavior into React with minimal design changes. Do not redesign the product during migration.

## 8. API Contract

Initial backend API:

```text
GET  /health
GET  /api/me
GET  /api/workflows/catalog
GET  /api/workflows/disclaimer
GET  /api/workflows/typeahead?kind=&q=&limit=
GET  /api/workflows/facet?workflow_id=&parameter=
GET  /api/workflows/{workflow_id}
POST /api/workflows/{workflow_id}/run
POST /api/workflows/evidence
GET  /api/documents/source?file=
GET  /api/documents/titles?file=&file=
POST /api/auth/sign-up
GET  /agent/*
```

No legacy API aliases in `corporate-rag`.

The new project must expose clean, intentional routes only. Do not add routes
solely to keep the old pilot HTML or old client code working.

## 9. Workflow Migration Strategy

Use `src/corporate_ner/workflows/v2/catalog.py` as the starting public catalog.

Migrated so far: `src/corporate_rag/workflows/catalog.py` now carries the current UI surface (`find.subject`, `find.organization`, `find.person`, `documents.search`, `capital.shareholdings`, `governance.poa.register`, `events.timeline`, `data_model.guide`) plus `data_model.dev_workflows` as dev-only.

Do not blindly migrate all v1 workflows. Classify every workflow:

```text
KEEP_PUBLIC      used by UI/client/agent and good enough
KEEP_INTERNAL    useful for agent or diagnostics, not visible in UI
REWRITE          useful concept, bad implementation or bad UX shape
ARCHIVE          useful historical note only
DROP             obsolete, duplicate, or pilot residue
```

Expected phase-1 public workflow groups:

- Find subject/person.
- Corporate profile and identifiers.
- Board/governance.
- Capital/shareholding.
- Documents search/source.
- Events/timeline.
- Data model/schema inspection.

Workflow coding rules:

- Query text stays parameterized.
- Each workflow has a stable id, title, category, description, parameters, output columns, and use cases.
- Each API package uses the same shape:
  - `router.py` for FastAPI routes and OpenAPI descriptions.
  - `models.py` for API schemas and local data models.
  - `repository.py` for graph/storage access and query templates.
- Repository modules should be functional by default. Do not add repository
  classes unless they carry real state or behavior beyond wrapping one or two
  functions.
- Modules should read top-down from higher-level exported entrypoints to
  lower-level helpers, query builders, registries, and raw query constants.
- Large Cypher may remain as strings in the package repository, but service/router modules should own only parameter building, validation, execution orchestration, and response shaping.
- Future cleanup can split very large repositories by package/domain only when the workflow catalog stops moving and the split improves readability.
- APOC may be used for readability or performance only after checking the matching Neo4j/APOC documentation and validating with `EXPLAIN`, `PROFILE`, and representative tests.
- Keep current graph schema assumptions explicit in docs.
- Add contract tests that validate catalog serialization and required params.
- Add snapshot tests for generated API payload shapes.

## 10. Agent Strategy

Keep the current agent infrastructure:

- LangChain model initialization.
- DeepAgents.
- MCP tool adapters.
- Chainlit UI.
- Internal and law modes.

Refactor responsibilities:

```text
agents/chainlit_app.py
  Chainlit lifecycle, auth, settings, message streaming.

agents/internal/factory.py
  Build internal agent session.

agents/internal/prompts.py
  Internal system prompt and tool whitelist.

agents/internal/sources.py
  Corporate citation rendering and source lookup.

agents/law/factory.py
  Build law agent session.

agents/law/prompts.py
  Law system prompt.

agents/law/citations.py
  Law citation sanitization and links.
```

Agent acceptance gates:

- Internal mode starts.
- Law mode starts.
- Model selector works.
- Agent version selector works if retained.
- Tool streaming works.
- `resolve_entity` disambiguation works.
- Source button opens corporate document sources.
- Law citations render article references.
- Chainlit auth works.
- Chat persistence works or is intentionally replaced.

## 11. MCP Strategy

Corporate MCP server:

- Keep read-only.
- Keep hand-written retrieval tools.
- Keep generated workflow tools from the active workflow catalog.
- Move Pydantic input schemas to `mcp/corporate/schemas.py`.
- Move retrieval logic to repositories where possible.
- Keep server assembly thin.

Law MCP server:

- Keep read-only.
- Preserve tools:
  - `list_corpus_acts`
  - `get_act_toc`
  - `search_law`
  - `get_article`
  - `get_neighbor_articles`
  - `get_article_citations`
- Preserve instruction: navigate act/TOC/article before final legal answer.

MCP runtime modes:

```text
stdio
  default for production app self-containment

streamable-http
  local development, testing, ops, optional sidecar
```

## 12. Ingestion Strategy

Corporate ingestion is the hardest area. Do not attempt a full rewrite before the
core app contracts are stable.

Phase-1 target: clean foundation and a truthful MVP pipeline.

Pipeline boundary:

```text
Document input
  -> store original
  -> normalize to PDF/image/text representation
  -> render pages
  -> OCR
  -> page vision observations
  -> chunks
  -> embeddings
  -> document summary/type
  -> FRBR structural graph write
  -> basic semantic extraction placeholder
  -> entity resolution placeholder
  -> receipt/report
```

Carry forward from `src/corporate_ner/load`:

- `normalize.py`
- `render.py`
- `vision.py`
- `chunker.py`
- `embed.py`
- `summarize.py`
- `persist.py`
- `types.py`
- parts of `pipeline.py`

Rewrite or defer:

- OCR module naming/import consistency.
- Entity extraction beyond document structure.
- Entity merge/deduplication.
- Completeness remediation.
- Human-in-the-loop graph fixes.

Target ingestion API:

```text
POST /api/ingestion/documents
GET  /api/ingestion/jobs/{job_id}
GET  /api/ingestion/jobs/{job_id}/receipt
```

Phase-1 implementation can run synchronously behind an admin-only endpoint or CLI. Production async job orchestration comes later.

Corporate ingestion TODO must not claim equivalence with the hand-built current graph until validated against a sample corpus.

## 13. Swiss Law Ingestion Strategy

Law ingestion is much more deterministic than corporate ingestion. Migrate earlier.

Carry forward:

- `swiss/law/ingestion/akn_parser.py`
- `swiss/law/ingestion/manifest.py`
- `swiss/law/ingestion/neo4j_writer.py`
- `swiss/law/ingestion/text_embedding_backfill.py`
- `swiss/law/graph/*`
- `swiss/law/mcp/*`
- `swiss/law/agent/*`
- `swiss/law/ingestion/manifests/swiss_corporate_law.json`

Target commands:

```bash
uv run corporate-rag law ensure-db
uv run corporate-rag law ingest-manifest
uv run corporate-rag law ingest-act <manifest_id>
uv run corporate-rag law report
uv run corporate-rag law backfill-embeddings
```

## 14. Data And Schema Strategy

Do not remodel the graph during app migration.

Rules:

- Preserve current corporate graph labels/properties/relationships.
- Preserve workflow assumptions around `BusinessSubject`, `Entity`, `Work`, `Expression`, `Manifestation`, `Item`, `Chunk`, `Class`, `Event`, `MonetaryAmount`, `Shareholding`.
- Preserve FRBR direction:
  - `Work -> HAS_REALIZATION -> Expression`
  - `Expression -> HAS_EMBODIMENT -> Manifestation`
  - `Manifestation -> HAS_EXEMPLAR -> Item`
- Preserve law graph database name unless explicitly changed.
- Add schema docs before changing schema.
- Any future graph fix must be a versioned migration, not a hidden script.

Target migration folder:

```text
src/corporate_rag/graph/migrations/
├── __init__.py
├── runner.py
├── 0001_constraints.py
├── 0002_indexes.py
└── README.md
```

## 15. AWS Deployment Architecture

Recommended production shape for 50-100 users:

```text
Route 53
  -> CloudFront
    -> S3 React static assets
    -> AWS WAF
    -> ALB HTTPS
      -> ECS Fargate service: corporate-rag-api
      -> ECS Fargate service: corporate-rag-agent
      -> private ECS/Cloud Map services: corporate-rag-mcp-corporate, corporate-rag-mcp-law

Neo4j
  Existing/self-managed Neo4j Enterprise on EC2
      - private subnet
      - EBS gp3
      - SSM access
      - S3 backup bucket
      - scheduled dump/snapshot

S3
  - source document staging
  - app artifacts
  - Neo4j backups/snapshots

Secrets Manager
  - OpenAI API key
  - Neo4j credentials
  - workflow auth secret
  - Chainlit auth secret

CloudWatch
  - logs
  - metrics
  - alarms

AWS WAF
  - public edge protection and rate limiting
```

Local Docker Compose shape:

```text
docker-compose.yml
  - Neo4j Enterprise matching the deployed/pilot version line
  - APOC installed through `NEO4J_PLUGINS`
  - `/plugins` mounted for n10s/neosemantics and other compatible plugins
  - `/var/lib/neo4j/import/ontologies` mounted for FIBO/RDF imports
  - graph runtime state mounted from `NEO4J_HOME`, normally `corporate-rag/.local/neo4j`
  - app service for local backend smoke tests
  - raw Neo4j Cypher MCP services for corporate (`neo4j`) and law (`law`) DBs
  - product MCP services once Phase 6 and Phase 8 are implemented
```

Deployment decisions:

- API and agent containers scale independently.
- Agent scaling beyond one task requires a persistent checkpointer/session store.
- MCP services are private internal services or agent sidecars in a phase-1 fallback, never hidden subprocesses inside the public API task.
- Neo4j is the bottleneck. Size and backup Neo4j before scaling app tasks.
- Long ingestion jobs must not run inside the public web task once production ingestion exists. Use ECS task/SQS later.

Initial ECS sizing:

```text
App:
  CPU: 1 vCPU
  Memory: 2-4 GB
  Desired count: 1
  Max count: 3

Neo4j EC2 fallback:
  Instance: r7i.large or r7i.xlarge to start
  Disk: gp3, 200+ GB, tuned after graph size
  Backup: daily dump + pre-migration snapshot
```

## 16. Execution Phases

### Phase 0: Freeze And Baseline

Goal: know exactly what must keep working.

TODO:

- [ ] Create branch/tag in `corporate-ner` named `pilot-final-baseline`.
- [ ] Export current workflow catalog JSON from `corpner-workflows`.
- [ ] Export current MCP tool list for corporate MCP.
- [ ] Export current MCP tool list for law MCP.
- [ ] Save current API route list from FastAPI.
- [ ] Save current frontend screenshots for `/`, workflow run, evidence drawer, document source, `/agent`.
- [ ] Save 10-20 representative workflow input/output fixtures from the live graph.
- [ ] Save 10 internal-agent test questions and expected evidence behavior.
- [ ] Save 10 law-agent test questions and expected citation behavior.
- [ ] Document required env vars.
- [ ] Document current production deploy commands and rollback procedure.

Acceptance:

- [ ] `docs/baseline/` in `corporate-rag` contains enough fixtures to detect migration regressions.

### Phase 1: Target Repo Foundation

Goal: make `corporate-rag` a real monolith skeleton.

TODO:

- [x] Update `pyproject.toml` with runtime dependencies.
- [x] Add `ruff`, `mypy --strict`, `pytest`, coverage config.
- [x] Add `src/corporate_rag` package with empty `__init__.py` files.
- [x] Add `settings.py` using Pydantic settings.
- [x] Add `cli.py` with Typer root command.
- [x] Add `app/main.py` with `create_app()`.
- [x] Add `/health`.
- [x] Add `README.md`.
- [x] Add `.env.example`.
- [x] Add `Makefile` commands:
  - `make lint`
  - `make typecheck`
  - `make test`
  - `make dev-backend`
  - `make dev-web`
- [x] Add minimal Dockerfile.
- [x] Add local `docker-compose.yml` for Neo4j, plugins, app, and MCP dependencies.

Acceptance:

- [x] `uv sync` works.
- [x] `uv run corporate-rag --help` works.
- [x] `uv run uvicorn corporate_rag.app.main:create_app --factory` starts.
- [x] `GET /health` returns 200.
- [x] `ruff`, `mypy --strict`, and `pytest` pass.

### Phase 2: Graph Client And Settings

Goal: migrate Neo4j access cleanly before workflows.

TODO:

- [x] Port `Neo4jClient` into `graph/neo4j_client.py`.
- [x] Replace private `_load_dotenv` with settings-driven config.
- [x] Add corporate graph database settings.
- [x] Add law graph database settings.
- [x] Add connection lifetime/acquisition/timeout settings.
- [x] Add read/write transaction methods.
- [ ] Add typed repository base helpers if needed.
- [x] Add tests for settings defaults.
- [x] Add tests for env overrides.
- [x] Add tests for client session database selection using fake driver where practical.

Acceptance:

- [x] No business module reads Neo4j env vars directly.
- [x] Graph clients can target corporate and law databases.
- [x] Existing connection tuning from old client is preserved.

### Phase 3: Workflow Backend

Goal: migrate the current useful workflow API.

TODO:

- [x] Port `workflows/models.py`.
- [x] Port `workflows/engine.py`.
- [x] Port current public `v2/catalog.py`.
- [x] Port only required query modules into package repositories.
- [x] Port facets into `facets/models.py`, `facets/repository.py`, and `facets/router.py`.
- [x] Port typeahead into `typeahead/models.py`, `typeahead/repository.py`, and `typeahead/router.py`.
- [x] Port evidence into `evidence/models.py`, `evidence/repository.py`, and `evidence/router.py`.
- [x] Port document source into `documents/models.py`, `documents/repository.py`, and `documents/router.py`.
- [x] Add `workflows/router.py`.
- [x] Add OpenAPI summaries, descriptions, tags, and response models for backend API modules.
- [x] Add Pydantic response models for API boundaries.
  - Done: public serializers hide internal Cypher, and workflow API endpoints expose explicit response models.
- [x] Add `GET /api/workflows/catalog`.
- [x] Add `GET /api/workflows/disclaimer`.
- [x] Add `GET /api/workflows/typeahead`.
- [x] Add `GET /api/workflows/facet`.
- [x] Add `GET /api/workflows/{workflow_id}`.
- [x] Add `POST /api/workflows/{workflow_id}/run`.
- [x] Add `POST /api/workflows/evidence`.
- [x] Add document routes under `/api/documents`.
- [x] Add catalog serialization tests.
- [x] Add workflow engine tests with fake graph client.
- [x] Add API tests with dependency override/fake repository.
- [ ] Add clean-contract regression fixtures for representative workflow scenarios.

Acceptance:

- [x] Current v2 catalog is available through the new API.
- [ ] Workflow execution returns the documented new API shape for representative fixtures.
- [x] Typeahead/facet/evidence/document source routes work.
- [x] No legacy aliases are exposed.

### Phase 4: React Workflows UI

Goal: replace `docs/internal/2026-05-12_workflows.html` with maintainable React.

TODO:

- [ ] Create `apps/web` Vite React JavaScript project.
- [ ] Copy visual tokens from current HTML/CSS.
- [ ] Implement layout and navigation.
- [ ] Implement workflow catalog loading.
- [ ] Implement workflow category filtering.
- [ ] Implement workflow detail panel.
- [ ] Implement parameter form.
- [ ] Implement typeahead parameter inputs.
- [ ] Implement facet selects.
- [ ] Implement workflow execution.
- [ ] Implement result table.
- [ ] Implement evidence drawer.
- [ ] Implement document source drawer.
- [ ] Implement disclaimer/document count.
- [ ] Implement auth/session handling for 401.
- [ ] Add production build output served by FastAPI.
- [ ] Add Playwright smoke test:
  - load app
  - open workflow
  - submit fake workflow through mocked backend or test fixture
  - open evidence/source drawer
- [ ] Do not add or preserve old HTML routes in `corporate-rag`.

Acceptance:

- [ ] UI looks materially the same or better.
- [ ] No business functionality lost.
- [ ] React build is served by backend in production.
- [ ] Local dev supports Vite dev server proxy to FastAPI.

### Phase 5: Auth And Chat Persistence

Goal: isolate auth/persistence from Chainlit and workflows.

TODO:

- [ ] Port current user/password storage logic from `chat/persistence.py`.
- [ ] Move auth models to `auth/models.py`.
- [ ] Move repository to `auth/repository.py`.
- [ ] Implement FastAPI dependency for current user.
- [ ] Implement admin role check.
- [ ] Port signup route.
- [ ] Keep Chainlit password auth callback using same repository.
- [ ] Add tests for password auth.
- [ ] Add tests for signup disabled/enabled.
- [ ] Add tests for workflow API auth.

Acceptance:

- [ ] One auth source protects workflows and Chainlit.
- [ ] Admin/dev-only routes are isolated.
- [ ] Auth code does not depend on workflow modules.

### Phase 6: Corporate MCP

Goal: migrate the internal agent tool surface.

TODO:

- [ ] Port corporate MCP schemas.
- [ ] Port corporate MCP handlers.
- [ ] Port retrieval modules.
- [ ] Port workflow tool registry generation.
- [ ] Register handwritten tools.
- [ ] Register workflow tools from active catalog.
- [ ] Add stdio runner.
- [ ] Add streamable-http runner.
- [ ] Add tool list contract test.
- [ ] Add handler tests with fake graph repositories.
- [ ] Add live optional test marker for a real Neo4j graph.

Acceptance:

- [ ] MCP exposes the same required tools as baseline.
- [ ] `resolve_entity`, search tools, chunk reads, document search, entity mentions, stats, and workflow tools work.
- [ ] Internal agent can connect through stdio.

### Phase 7: Internal Agent

Goal: migrate Chainlit internal mode.

TODO:

- [ ] Port `agents/chainlit_app.py` from current `chat/chat_app.py`.
- [ ] Port internal `agent_factory.py`.
- [ ] Port internal prompt and tool whitelist.
- [ ] Port source/citation rendering.
- [ ] Port task list/tool streaming UI.
- [ ] Port disambiguation action for `resolve_entity`.
- [ ] Wire stdio corporate MCP by default.
- [ ] Add model selector.
- [ ] Add agent version selector if still useful.
- [ ] Add tests for prompt/tool whitelist.
- [ ] Add tests for citation rendering.
- [ ] Add tests for source lookup logic.
- [ ] Add Chainlit route smoke test.

Acceptance:

- [ ] `/agent` opens.
- [ ] Internal mode can answer baseline questions using MCP tools.
- [ ] Source button works.
- [ ] No direct graph reads from the agent except citation/source rendering code that is explicitly isolated.

### Phase 8: Swiss Law Graph, MCP, And Agent

Goal: migrate deterministic law side.

TODO:

- [ ] Move law graph models/schema/client into `law/`.
- [ ] Move law ingestion into `ingestion/law/`.
- [ ] Move law MCP into `mcp/law/`.
- [ ] Move law agent factory/prompts/citations into `agents/law/`.
- [ ] Preserve manifest for 9 acts.
- [ ] Add CLI commands for law ingest/report/backfill.
- [ ] Add parser tests from old `test_swiss_law_akn_parser.py`.
- [ ] Add MCP handler tests from old `test_swiss_law_mcp_handlers.py`.
- [ ] Add citation tests.
- [ ] Add optional live law graph report test.

Acceptance:

- [ ] Law database can be created and ingested from manifest.
- [ ] Law MCP exposes required tools.
- [ ] Law mode in Chainlit answers with article citations.

### Phase 9: Corporate Ingestion Foundation

Goal: create the proper place for ingestion without pretending full graph-building is solved.

TODO:

- [ ] Port structural pipeline modules from `load`.
- [ ] Define `IngestionJob`, `IngestionReceipt`, `DocumentInput`, `IngestionError`.
- [ ] Add local document storage.
- [ ] Add S3 document storage interface and implementation.
- [ ] Add admin-only CLI ingestion command.
- [ ] Add admin-only API upload route if needed.
- [ ] Preserve FRBR structural write behavior.
- [ ] Preserve chunk embedding behavior.
- [ ] Preserve document summary/doc_type behavior.
- [ ] Add dry-run mode that produces receipt without graph writes.
- [ ] Add tests for normalization.
- [ ] Add tests for chunking.
- [ ] Add tests for receipt shape.
- [ ] Add tests for persist Cypher shape using fake client.
- [ ] Add `docs/ingestion.md` with honest quality limitations.

Acceptance:

- [ ] One document can flow through structural ingestion in dev.
- [ ] Pipeline produces Work/Expression/Manifestation/Item/Chunk structure.
- [ ] Semantic entity extraction and dedup are documented as next-stage work.

### Phase 10: Infrastructure

Goal: replace ad hoc EC2 deploy scripts with maintainable AWS infra.

TODO:

- [ ] Decide Neo4j Aura vs self-managed EC2.
- [ ] Add `infra/README.md`.
- [ ] Add CDK app.
- [ ] Add network stack:
  - VPC
  - public/private subnets
  - security groups
- [ ] Add app stack:
  - ECR repository
  - ECS cluster
  - Fargate service
  - ALB
  - HTTPS certificate
  - health check
  - autoscaling policy
- [ ] Add secrets stack:
  - OpenAI API key secret
  - Neo4j URI/user/password secret
  - auth secrets
- [ ] Add storage stack:
  - document bucket
  - backup bucket
  - access policies
- [ ] Add observability:
  - CloudWatch log groups
  - dashboard
  - alarms for 5xx, task restarts, high CPU/memory
- [ ] Add Neo4j EC2 stack if not using Aura.
- [ ] Add backup/snapshot scripts for Neo4j EC2.
- [ ] Add deployment runbook.
- [ ] Add rollback runbook.
- [ ] Add smoke test script for deployed URL.

Acceptance:

- [ ] Fresh environment can be deployed from commands in docs.
- [ ] Secrets are not stored in repo.
- [ ] App health check is monitored.
- [ ] Neo4j backup/restore path is tested.

### Phase 11: Cleanup And Deletion

Goal: keep only code that belongs to the clean monolith.

TODO:

- [ ] Confirm no legacy API aliases were introduced.
- [ ] Confirm the old HTML workflow console was not migrated.
- [ ] Remove old v1 workflows not classified as keep/rewrite.
- [ ] Remove OpenClaw/Argus loop references.
- [ ] Remove completeness runner unless redefined as ingestion quality tooling.
- [ ] Remove distributed worker fleet code if replaced by ECS/AWS infra.
- [ ] Remove one-off remediation scripts after converting necessary ones to migrations/docs.
- [ ] Remove generated runtime state.
- [ ] Remove outdated docs.
- [ ] Update README and docs.
- [ ] Run full tests, typecheck, lint.

Acceptance:

- [ ] Repository contains no unused primary modules.
- [ ] README describes only implemented behavior.
- [ ] Docs do not point to obsolete commands.

### Phase 12: Production Hardening

Goal: make it safe for real client usage.

TODO:

- [ ] Add request IDs.
- [ ] Add structured logs.
- [ ] Add error response schema.
- [ ] Add API rate limiting or WAF rule.
- [ ] Add auth lockout/backoff.
- [ ] Add backup restore drill.
- [ ] Add graph read timeout controls.
- [ ] Add workflow query timeout policy.
- [ ] Add agent max tool iterations/config.
- [ ] Add cost logging for LLM calls if available.
- [ ] Add deployment smoke tests to CI.
- [ ] Add Playwright production smoke.
- [ ] Add incident runbook.

Acceptance:

- [ ] App can be restarted without losing critical state.
- [ ] Backups are restorable.
- [ ] Failed deploy can roll back.
- [ ] Operational owner can diagnose 5xx, Neo4j failures, and agent failures.

## 17. Suggested Implementation Order For Cheap Models

Use one small task per PR/session. Avoid asking a cheap model to "migrate workflows" broadly.

Good task shape:

```text
Port exactly one module or one route.
Read old source path X.
Create target path Y.
Add tests Z.
Do not change unrelated modules.
Run command C.
```

Recommended task queue:

1. `pyproject` + skeleton.
2. Settings.
3. Health route.
4. Neo4j client.
5. Workflow models.
6. Workflow engine.
7. One query module.
8. Current v2 catalog shell.
9. Catalog API route.
10. Workflow run API route.
11. Typeahead.
12. Facets.
13. Evidence.
14. Document source.
15. React app skeleton.
16. React catalog view.
17. React workflow form.
18. React results table.
19. React evidence drawer.
20. Auth repository.
21. Signup route.
22. Corporate MCP schemas.
23. Corporate MCP handlers.
24. Corporate MCP server.
25. Internal agent factory.
26. Chainlit app internal mode.
27. Source citations.
28. Law graph client/schema.
29. Law ingestion parser.
30. Law MCP server.
31. Law agent mode.
32. Corporate ingestion types.
33. Corporate ingestion normalize/render/chunk.
34. Corporate ingestion persist structural graph.
35. Dockerfile.
36. Docker compose.
37. CDK network stack.
38. CDK app stack.
39. Secrets/storage stacks.
40. Deploy runbook.

## 18. Clean-Contract Checklist

Workflow behavior:

- [ ] Catalog categories match the intended public catalog.
- [ ] Each workflow returns documented columns for the new API.
- [ ] Parameter coercion is explicit, tested, and documented.
- [ ] Typeahead returns expected candidates.
- [ ] Facets return expected values.
- [ ] Evidence lookup returns source docs/chunks.
- [ ] Document source returns readable chunks/text.

Internal agent behavior:

- [ ] Resolves AEH subject family.
- [ ] Answers board/current governance question.
- [ ] Answers capital/shareholding question.
- [ ] Finds signed documents by person.
- [ ] Uses workflow tools for structured questions.
- [ ] Uses search/read tools for close reading.
- [ ] Provides citations/source markers.

Law agent behavior:

- [ ] Lists corpus acts.
- [ ] Opens act TOC.
- [ ] Reads concrete article.
- [ ] Searches law paragraphs.
- [ ] Returns neighboring articles when needed.
- [ ] Renders citations.

Deployment behavior:

- [ ] Local dev works.
- [ ] Container starts.
- [ ] Deployed app health check passes.
- [ ] `/` works.
- [ ] `/api/workflows/catalog` works.
- [ ] `/agent` works.
- [ ] Corporate MCP stdio works.
- [ ] Law MCP stdio works.

## 19. Documentation Plan

Create only current, useful docs:

```text
docs/
├── architecture.md       # module boundaries and runtime shape
├── workflows.md          # current public workflows and how to add one
├── agents.md             # internal/law agent architecture and prompts/tools
├── ingestion.md          # corporate + law ingestion, limitations, commands
├── data_model.md         # graph labels/relationships relied on by app
├── deployment.md         # AWS deploy and rollback
├── operations.md         # backups, smoke tests, incidents
└── adr/
```

Do not migrate historical remediation plans as primary docs. If needed, archive them under:

```text
docs/archive/pilot/
```

## 20. CI Plan

Minimum CI:

```text
Python:
  uv sync
  ruff check .
  ruff format --check .
  mypy --strict src tests
  pytest

Frontend:
  npm ci
  npm run build
  npm run test --if-present

Docker:
  docker build .
```

Later CI:

- Playwright smoke against built app.
- Optional Neo4j integration job with test container.
- Optional deployed smoke test after CDK deploy.

## 21. Deletion Candidates From Old Project

Likely do not migrate as product code:

- `openclaw/`
- `argus_loop/`
- `completeness/` unless redefined as graph quality tools.
- `graph_mcp/` write-oriented Argus surface unless future graph mutation workflow is explicitly planned.
- Old `docs/internal/*remediation*`.
- Old `docs/internal/*openclaw*`.
- Runtime folders under `distributed/.runtime`.
- One-off scripts in `scripts/remediate_*` unless converted to migrations.
- Full `ontologies/fibo` checkout unless runtime needs local ontology source.

Keep or rewrite:

- `graph_tools/client.py` -> `graph/neo4j_client.py`.
- `graph_tools/capital_projection.py` if current workflows depend on it.
- `authority/registry.py` if v2 workflows depend on event authority logic.
- Tests that encode current behavior.

## 22. Open Decisions

Resolve before Phase 10:

- [ ] CDK vs Terraform.
- [ ] Keep basic password auth or move to Cognito/OIDC.
- [ ] Whether document upload/ingestion is available to clients in pilot v2 or admin-only.
- [ ] Whether current graph database name changes from `neo4j` to `corporate`.
- [ ] Whether law graph stays in same Neo4j instance as corporate graph.

Recommended defaults:

- Use CDK Python.
- Split API, Chainlit/agent, and MCP services in production; local development may keep a single app command for convenience.
- Keep basic password auth for pilot continuity.
- Use admin-only ingestion.
- Keep current Neo4j database names during migration, rename only after backup/restore rehearsal.
- Keep the existing Neo4j Enterprise EC2 deployment unless a separate migration plan explicitly replaces it.

## 23. First Five Concrete Tasks

Task 1:

- [x] Create project skeleton in `corporate-rag`.
- [x] Add Python tooling.
- [x] Add `corporate_rag.app.main:create_app`.
- [x] Add `/health`.
- [x] Add tests.

Task 2:

- [x] Add Pydantic settings.
- [x] Add `.env.example`.
- [ ] Add tests for env parsing.
  - Done: explicit settings default/value tests.
  - Remaining: environment variable parsing tests.

Task 3:

- [x] Port Neo4j client.
- [x] Add graph settings.
- [x] Add fake-driver tests.

Task 4:

- [x] Port workflow models and engine.
- [x] Add unit tests.

Task 5:

- [ ] Port active v2 workflow catalog and catalog API.
- [ ] Add contract test comparing serialized catalog shape to baseline fixture.
  - Done: workflow API shell and public serializers.
  - Remaining: accepted v2 catalog transfer and baseline fixture comparison.
