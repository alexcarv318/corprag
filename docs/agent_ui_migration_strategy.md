# Agent UI Migration Strategy

Status: proposed architecture note  
Date: 2026-06-14  
Related plan: `PILOT_REFACTOR_MASTER_PLAN.md`

## Executive Summary

The new `corporate-rag` product should not keep Chainlit as the primary production UI for the agent surface.

The recommended direction is:

- Build a native React agent UI inside `apps/web`.
- Extract the useful agent runtime behavior from the old Chainlit callbacks into clean backend services.
- Expose a small, product-owned `/api/agent/*` contract from FastAPI.
- Keep Chainlit only as a temporary migration/debug adapter if needed.
- Use Chainlit source code as a reference for chat interaction patterns, not as a frontend dependency to copy wholesale.

This gives the product one application shell, one authentication system, one routing model, one visual language, and one backend contract surface. It also avoids importing Chainlit's broad UI architecture into a repository whose main goal is to become cleaner and more maintainable than the pilot.

## Why This Matters

The current pilot mounts Chainlit at `/agent`. That was a pragmatic way to get a working conversational interface quickly, but it creates long-term product friction:

- The workflows UI and agent UI are separate applications.
- Authentication is split across parent FastAPI routes and Chainlit callbacks.
- Navigation, layout, user menu, styling, and session behavior are harder to unify.
- Product-specific features such as document drawers, workflow handoff, citations, law references, and admin-only traces are awkward to compose across the app boundary.
- Deep customization of Chainlit tends to become CSS/JavaScript patching rather than clean product code.

For `corporate-rag`, the agent should be a first-class feature of the React frontend, not a mounted neighboring application.

## Current Pilot Behavior To Preserve

The old `corporate-ner` Chainlit app currently provides several useful behaviors that should be migrated deliberately:

- Password-based user authentication backed by local storage.
- Two agent modes:
  - internal corporate archive agent
  - Swiss law agent
- Mode-specific starters.
- Model selection.
- Internal-agent version selection.
- Streaming assistant responses.
- LangChain/DeepAgents callback integration.
- Tool progress through Chainlit callback events.
- Corporate document citations and source actions.
- Swiss law citation linking and answer sanitization.
- Chat persistence through Chainlit-compatible tables.
- Human feedback storage.
- Signup flow for local/pilot use.

These are product capabilities. They should move into product modules with explicit contracts. Chainlit should not remain the owner of these behaviors.

## Chainlit Findings

Chainlit remains a strong reference implementation for fast conversational prototypes.

The current Chainlit repository has these relevant characteristics:

- The project is open source under Apache-2.0.
- The root repository contains `backend`, `frontend`, `libs`, `docs`, and Cypress tests.
- The frontend is a Vite/React application.
- Chainlit also publishes `@chainlit/react-client`, described as a WebSocket client for connecting to Chainlit apps.
- The frontend stack is intentionally broad: React, TypeScript, Recoil, Socket.IO, Radix, Tailwind, Plotly, PDF rendering, media players, markdown/math/rendering packages, forms, and more.
- Chainlit's FastAPI integration mounts Chainlit as a sub-application through `mount_chainlit`.
- Chainlit documentation recommends header authentication when Chainlit is mounted under a FastAPI parent app.
- Chainlit supports streaming for messages and steps.
- Chainlit data persistence is optional; by default, generated chats and elements are not persisted unless a data layer is configured.

The important conclusion: Chainlit's source code can simplify discovery of chat concepts and event names, but importing or copying its frontend architecture would work against this refactor's cleanliness goals.

## Approaches Considered

### Option 1: Keep Mounted Chainlit In Production

Runtime shape:

```text
React workflows app: /, /workflows
Chainlit app:        /agent
FastAPI API:         /api/*
```

Benefits:

- Fastest short-term migration.
- Preserves existing Chainlit behavior with minimal rewrite.
- Chainlit already handles chat UI, streaming, settings, and persistence hooks.

Costs:

- Product remains split into two applications.
- Shared auth requires extra glue.
- UI customization remains limited.
- Harder to reuse the same document drawers, layout, navigation, and workflow links.
- Future cleanup becomes harder because Chainlit remains a production dependency and product boundary.

Recommendation: acceptable only as a short-lived bridge, not as the target architecture.

### Option 2: Embed Or Heavily Customize Chainlit

Runtime shape:

```text
React app shell
  -> iframe or embedded link to /agent
  -> custom Chainlit CSS/JS/theme patches
```

Benefits:

- Gives an illusion of integration quickly.
- Can keep most of the current Chainlit app intact.

Costs:

- Still two applications.
- Styling and routing integration will be brittle.
- Auth/session behavior can become confusing.
- Accessibility, layout, mobile behavior, and cross-feature interactions are harder to control.
- This tends to create patch files that are difficult to reason about.

Recommendation: avoid except for a temporary demo.

### Option 3: Use `@chainlit/react-client` Directly

Runtime shape:

```text
React app owns UI
React app imports @chainlit/react-client
Backend still speaks Chainlit Socket.IO protocol
```

Benefits:

- Gives a custom React UI while reusing Chainlit's client protocol implementation.
- May accelerate a prototype if the backend remains Chainlit-compatible.
- Useful as a reference for event semantics.

Costs:

- Couples the product frontend to Chainlit's Socket.IO protocol.
- Pulls in Recoil and Chainlit client state assumptions.
- Keeps the backend shaped around Chainlit events instead of product contracts.
- Conflicts with the target frontend rule: JavaScript, no heavyweight state manager, fetch-based API client unless streaming truly requires more.
- Makes it harder to remove Chainlit later.

Recommendation: do not use as a production dependency. It can be studied as reference code.

### Option 4: Fork Or Vendor Chainlit Frontend

Runtime shape:

```text
apps/web contains copied/forked Chainlit frontend pieces
corporate-rag modifies them over time
```

Benefits:

- Maximum reuse of existing chat UI behavior.
- Source is available and permissively licensed.

Costs:

- Large dependency and code volume enters the repo.
- Much of Chainlit's generic functionality is not needed.
- The codebase becomes partly a fork maintenance project.
- TypeScript/Tailwind/Recoil conventions conflict with the phase-1 frontend direction.
- Security updates and upstream changes become a recurring chore.
- Product code stops reading as a focused first-class implementation.

Recommendation: reject for cleanliness reasons.

### Option 5: Native React Agent UI With Product-Owned Backend API

Runtime shape:

```text
Browser
  -> React app
      -> /workflows
      -> /agent
      -> /documents
      -> shared layout/auth/navigation

FastAPI
  -> /api/auth/*
  -> /api/workflows/*
  -> /api/agent/*
  -> /api/documents/*
```

Benefits:

- Full control over UI and UX.
- One authentication system.
- One application shell.
- Clean backend contracts.
- Easier citation/document/workflow integration.
- Easier test strategy.
- Chainlit can be removed from production when parity is reached.

Costs:

- Requires implementing chat primitives directly.
- Requires a product streaming contract.
- Requires session/message persistence endpoints.

Recommendation: choose this as the target architecture.

## Target Decision

Adopt Option 5.

The production agent UI should be a native React feature under `apps/web/src/features/agent`. Chainlit may remain temporarily under a non-primary path such as `/chainlit-dev` or `/agent-legacy` while parity is being checked, but the product target should not mount Chainlit at `/agent`.

The current master plan should eventually change from this:

```text
Browser
  -> React workflows app: /, /workflows
  -> Chainlit agent app: /agent
```

to this:

```text
Browser
  -> React product app
      -> /workflows
      -> /agent
      -> /documents
```

## Clean Architecture Principles

The migration should follow these rules:

- Do not copy the Chainlit frontend into `apps/web`.
- Do not make React components depend on Chainlit Python concepts.
- Do not expose Chainlit event names as the long-term public API unless they are intentionally renamed into product language.
- Do not keep auth inside Chainlit callbacks.
- Do not make agent sessions live in hidden globals.
- Do not let MCP details leak into UI contracts except through explicit trace/debug models.
- Keep citations and sources as first-class product objects.
- Keep workflow and document APIs reusable by both workflows and agent features.
- Keep the first UI implementation smaller than Chainlit, not equivalent to Chainlit.

## Proposed Backend Modules

```text
src/corporate_rag/
|-- agents/
|   |-- models.py
|   |-- router.py
|   |-- runner.py
|   |-- sessions.py
|   |-- persistence.py
|   |-- citations.py
|   |-- settings.py
|   |-- legacy_chainlit.py          # optional temporary adapter only
|   |-- internal/
|   |   |-- factory.py
|   |   |-- prompts.py
|   |   |-- sources.py
|   |   |-- tools.py
|   |-- law/
|       |-- factory.py
|       |-- prompts.py
|       |-- citations.py
|-- auth/
|   |-- models.py
|   |-- router.py
|   |-- repository.py
|   |-- password_auth.py
|-- documents/
    |-- router.py
    |-- repository.py
    |-- models.py
```

Temporary Chainlit compatibility should be isolated. If it exists, it should be clearly marked as a bridge and excluded from core service design.

## Proposed Frontend Modules

```text
apps/web/src/
|-- api/
|   |-- agent.js
|   |-- auth.js
|   |-- client.js
|   |-- documents.js
|   |-- workflows.js
|-- features/
|   |-- agent/
|   |   |-- AgentPage.jsx
|   |   |-- AgentHeader.jsx
|   |   |-- AgentModeSelect.jsx
|   |   |-- ChatComposer.jsx
|   |   |-- MessageList.jsx
|   |   |-- MessageBubble.jsx
|   |   |-- CitationList.jsx
|   |   |-- SourceDrawer.jsx
|   |   |-- SessionList.jsx
|   |   |-- ToolTrace.jsx
|   |   |-- useAgentStream.js
|   |-- documents/
|   |-- shell/
|   |-- workflows/
|-- styles/
    |-- agent.css
    |-- base.css
    |-- theme.css
```

Keep state local at first: React hooks and small feature reducers are enough. Avoid a global state manager unless the UI starts sharing complex live state across unrelated routes.

## API Contract

### Auth

The same auth system should guard workflows, documents, and agent routes.

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/me
```

Suggested `GET /api/me` response:

```json
{
  "id": "user_123",
  "username": "alex",
  "role": "admin",
  "capabilities": ["agent:use", "workflows:use", "admin:debug"]
}
```

### Agent Metadata

```text
GET /api/agent/config
```

Suggested response:

```json
{
  "default_mode": "internal",
  "modes": [
    {
      "id": "internal",
      "label": "Corporate archive",
      "supports_agent_versions": true,
      "supports_citations": true
    },
    {
      "id": "law",
      "label": "Swiss law",
      "supports_agent_versions": false,
      "supports_citations": true
    }
  ],
  "models": [
    {"id": "gpt-4.1", "label": "GPT-4.1", "default": true}
  ],
  "agent_versions": [
    {"id": "current", "label": "Current", "default": true}
  ],
  "starters": {
    "internal": [
      {"label": "Current board", "message": "Who is on the board of Acer European Holdings today?"}
    ],
    "law": [
      {"label": "AG formation", "message": "Under the Swiss Code of Obligations, what are the minimum formation requirements for a Swiss stock corporation?"}
    ]
  }
}
```

### Sessions

```text
GET    /api/agent/sessions
POST   /api/agent/sessions
GET    /api/agent/sessions/{session_id}
PATCH  /api/agent/sessions/{session_id}
DELETE /api/agent/sessions/{session_id}
```

Suggested session model:

```json
{
  "id": "session_123",
  "title": "Board duties question",
  "mode": "law",
  "model_id": "gpt-4.1",
  "agent_version": null,
  "created_at": "2026-06-14T12:00:00Z",
  "updated_at": "2026-06-14T12:03:00Z"
}
```

### Messages

```text
GET  /api/agent/sessions/{session_id}/messages
POST /api/agent/sessions/{session_id}/messages
```

Suggested message model:

```json
{
  "id": "msg_123",
  "session_id": "session_123",
  "role": "assistant",
  "content": "The answer text...",
  "status": "complete",
  "created_at": "2026-06-14T12:01:00Z",
  "citations": [],
  "tool_events": []
}
```

### Streaming

Prefer Server-Sent Events for phase 1 unless the product needs true bidirectional interactive features during a run. SSE keeps the architecture simple:

```text
POST /api/agent/sessions/{session_id}/runs
GET  /api/agent/runs/{run_id}/events
POST /api/agent/runs/{run_id}/cancel
```

The `POST /runs` request creates the user message and starts a run:

```json
{
  "message": "Who is on the board today?",
  "mode": "internal",
  "model_id": "gpt-4.1",
  "agent_version": "current"
}
```

The event stream should use product-owned event names:

```text
event: run_started
data: {"run_id":"run_123","assistant_message_id":"msg_456"}

event: message_delta
data: {"message_id":"msg_456","text":"The board"}

event: tool_started
data: {"id":"tool_1","name":"find_directors","label":"Searching directors"}

event: tool_updated
data: {"id":"tool_1","summary":"Found 4 candidates"}

event: citations_updated
data: {"message_id":"msg_456","citations":[...]}

event: message_completed
data: {"message_id":"msg_456","content":"Final rendered answer...","citations":[...]}

event: run_failed
data: {"run_id":"run_123","error":"..."}
```

Use WebSockets later only if these become required:

- live user answers in the middle of a run
- realtime audio
- collaborative sessions
- frequent bidirectional control messages

### Feedback

```text
POST /api/agent/messages/{message_id}/feedback
```

Suggested request:

```json
{
  "value": 1,
  "comment": "Useful answer with correct sources."
}
```

## Backend Service Shape

The key extraction is an agent runner that knows nothing about Chainlit.

```python
class AgentRunner:
    async def stream_reply(
        self,
        request: AgentRunRequest,
        user: AuthenticatedUser,
    ) -> AsyncIterator[AgentEvent]:
        ...
```

Suggested event hierarchy:

```python
class AgentEvent(BaseModel):
    type: str

class MessageDeltaEvent(AgentEvent):
    type: Literal["message_delta"] = "message_delta"
    message_id: str
    text: str

class ToolStartedEvent(AgentEvent):
    type: Literal["tool_started"] = "tool_started"
    id: str
    name: str
    label: str

class MessageCompletedEvent(AgentEvent):
    type: Literal["message_completed"] = "message_completed"
    message_id: str
    content: str
    citations: list[Citation]
```

The runner should own:

- mode selection
- model selection
- agent version selection
- session history loading
- LangChain/DeepAgents invocation
- token streaming
- tool event translation
- final citation rendering
- persistence updates
- cancellation checks

The router should own:

- auth dependency
- request validation
- response serialization
- SSE formatting
- HTTP status codes

The factories should own:

- corporate agent construction
- law agent construction
- MCP client setup
- prompt selection

## Persistence Model

The new product should not preserve Chainlit table names as the primary schema unless that is explicitly chosen for migration convenience.

Recommended product tables:

```text
agent_sessions
  id
  user_id
  title
  mode
  model_id
  agent_version
  metadata_json
  created_at
  updated_at
  archived_at

agent_messages
  id
  session_id
  role
  content
  status
  created_at
  completed_at
  metadata_json

agent_citations
  id
  message_id
  kind
  label
  file
  title
  chunk_ids_json
  href
  metadata_json

agent_tool_events
  id
  run_id
  message_id
  name
  status
  input_json
  output_json
  summary
  started_at
  completed_at

agent_feedback
  id
  message_id
  user_id
  value
  comment
  created_at
```

If existing Chainlit history is valuable, write a one-time importer from Chainlit tables to product tables. Do not keep Chainlit persistence as the long-term schema just because it already exists.

## Citation And Source Design

Citations should be a shared product model, not a Chainlit action payload.

Suggested citation model:

```json
{
  "id": "cit_1",
  "kind": "corporate_document",
  "label": "[1]",
  "file": "document.pdf",
  "title": "Board resolution",
  "chunk_ids": ["chunk_1", "chunk_2"],
  "href": "/documents/source?file=document.pdf",
  "metadata": {}
}
```

For Swiss law:

```json
{
  "id": "cit_2",
  "kind": "swiss_law",
  "label": "CO 716a",
  "title": "Swiss Code of Obligations Art. 716a",
  "href": "/law/articles/CO/716a",
  "metadata": {"code": "CO", "article": "716a"}
}
```

The React UI can then render a consistent citation strip, source drawer, and document preview across workflows and chat.

## What To Reuse From Chainlit

Use Chainlit source code as a guide for:

- Message lifecycle vocabulary.
- Streaming event sequencing.
- Thread/session concepts.
- Feedback concepts.
- Element/source rendering ideas.
- How Socket.IO can support richer bidirectional behavior if needed later.
- Edge cases around reconnecting and resuming threads.

Do not reuse wholesale:

- Chainlit's full frontend app.
- Chainlit's generic element system.
- Chainlit's Recoil state model.
- Chainlit's full Socket.IO event surface.
- Chainlit's settings UI abstraction.
- Chainlit table names as product domain names.

If small snippets are adapted, preserve Apache-2.0 attribution as required and record the source path in a short comment or documentation note. Prefer independent implementation for simple UI components and API clients.

## Minimum Product UI

The phase-1 React agent UI should be intentionally smaller than Chainlit.

Required:

- Agent route at `/agent`.
- Shared app shell and authenticated user menu.
- Session list.
- New session button.
- Mode selector: corporate archive / Swiss law.
- Model selector.
- Agent version selector for corporate mode only.
- Starter prompts.
- Message list.
- Markdown rendering for assistant messages.
- Streaming assistant response.
- Stop/cancel button.
- Retry last user message.
- Citation list.
- Source drawer using shared document APIs.
- Feedback controls.
- Empty, loading, error, and reconnect states.

Not required in phase 1:

- Audio.
- Arbitrary Chainlit elements.
- Arbitrary Chainlit actions.
- User-uploaded files in chat.
- Plotly/media/pdf embedding inside chat messages.
- Chat settings framework.
- MCP server management from the browser.
- Full tool chain-of-thought display for normal users.

Admin/debug-only later:

- Tool trace timeline.
- Raw MCP calls.
- Token counts.
- Prompt/version metadata.
- Run replay.

## Migration Phases

### Phase 1: Extract Runtime From Chainlit

Goal: make agent behavior callable without Chainlit.

Tasks:

- Move mode definitions into `corporate_rag.agents.models`.
- Move model and agent-version selection into explicit settings/services.
- Create `AgentRunner.stream_reply`.
- Move citation rendering into `corporate_rag.agents.citations`.
- Move corporate source resolution into reusable document/source services.
- Keep the old Chainlit app as a thin adapter if needed.

Acceptance checks:

- Unit tests can call `AgentRunner` without importing Chainlit.
- Corporate and law modes can be selected explicitly.
- Citation rendering can be tested independently.

### Phase 2: Add Product Agent API

Goal: expose backend contracts for React.

Tasks:

- Add `/api/agent/config`.
- Add session CRUD endpoints.
- Add message list endpoint.
- Add run creation endpoint.
- Add SSE run event endpoint.
- Add feedback endpoint.
- Add auth dependency to all routes.

Acceptance checks:

- Contract tests cover auth, config, sessions, messages, runs, and feedback.
- SSE event serialization is tested without needing a browser.
- No route depends on Chainlit internals.

### Phase 3: Build Native React Agent UI

Goal: implement the product-owned `/agent` route.

Tasks:

- Add `features/agent` components.
- Add `api/agent.js`.
- Implement session list and active session state.
- Implement composer and streaming hook.
- Render citations and source drawer.
- Add feedback controls.
- Add loading/error/empty states.

Acceptance checks:

- Playwright smoke test can log in, open `/agent`, send a message, receive streamed text, and open a source/citation when present.
- Mobile and desktop layouts do not overlap.
- The app shell remains shared with workflows.

### Phase 4: Compare Against Chainlit

Goal: preserve useful behavior before deleting the old surface.

Tasks:

- Run side-by-side prompts in Chainlit and native React.
- Compare final text, citations, and mode behavior.
- Verify corporate source actions have native equivalents.
- Verify Swiss law citation output.
- Check session persistence and feedback.

Acceptance checks:

- A documented parity checklist passes for the features the product actually needs.
- Any intentionally dropped Chainlit feature is listed as out of scope.

### Phase 5: Remove Or Demote Chainlit

Goal: keep production clean.

Tasks:

- Remove Chainlit mount from production app.
- Optionally keep `/chainlit-dev` behind an admin/dev flag for a short period.
- Remove Chainlit-specific frontend assets.
- Remove Chainlit table dependency after data migration.
- Remove Chainlit package dependency if no longer needed.

Acceptance checks:

- `ruff`, `mypy --strict`, and `pytest` pass.
- React build and Playwright smoke tests pass.
- No production route requires Chainlit.

## Testing Strategy

Backend:

- Unit tests for `AgentRunner` event translation.
- Unit tests for corporate citation parsing and source payload generation.
- Unit tests for law citation linking/sanitization.
- Contract tests for all `/api/agent/*` endpoints.
- Persistence tests for sessions, messages, citations, tool events, and feedback.
- Cancellation tests for long-running streams.

Frontend:

- Component tests only after the UI stabilizes.
- Playwright smoke tests early:
  - login
  - open workflows
  - open agent
  - create session
  - send message
  - observe streaming
  - open citation/source drawer
  - submit feedback

Operational:

- Log each run with `run_id`, `session_id`, `user_id`, `mode`, `model_id`, duration, status, and error class.
- Avoid logging full user messages by default in production unless explicitly configured.
- Store enough metadata to debug failed runs without leaking sensitive content into logs.

## Security And Auth

The new app should use one auth system for all product routes.

Recommended baseline:

- FastAPI owns login/logout/current-user routes.
- Auth cookie is HTTP-only, secure in production, same-site strict or lax depending on deployment needs.
- All `/api/workflows/*`, `/api/documents/*`, and `/api/agent/*` routes use the same `current_user` dependency.
- Roles/capabilities are returned by `/api/me` and enforced server-side.
- Admin-only traces are never controlled only by frontend visibility.

If Chainlit remains temporarily mounted, use parent-auth delegation/header auth only as a bridge. Do not keep Chainlit password auth as the product source of truth.

## Repository Cleanliness Rules

To protect the refactor goal:

- Keep Chainlit bridge code in one obvious module if it exists.
- Name modules after product domains, not migration history.
- Avoid folders named `legacy`, `v2`, or `chainlit_clone` in runtime code.
- Do not vendor external frontend source trees.
- Do not preserve old import paths.
- Keep API serializers explicit and Pydantic-backed.
- Keep React components small and product-specific.
- Keep generic UI components in `components/`; keep agent behavior in `features/agent/`.
- Document any intentionally retained Chainlit dependency with a removal condition.

## Open Questions

- Should phase 1 use local SQLite for auth/session persistence, or should the new product introduce Postgres early for production readiness?
- Should chat history be migrated from current Chainlit tables, or is it acceptable to start fresh in `corporate-rag`?
- Should `/agent` support user-uploaded documents in phase 1, or should document ingestion remain a separate workflow?
- Should tool traces be visible to normal users as simplified progress, or only to admins as debug details?
- Should streaming use SSE initially, or does the product need WebSockets immediately for planned bidirectional features?

## Recommendation For The Master Plan

Update the master plan's target architecture and frontend tree to make the native agent UI explicit.

Replace:

```text
features/agent/
    AgentLink.jsx
```

with:

```text
features/agent/
    AgentPage.jsx
    AgentHeader.jsx
    AgentModeSelect.jsx
    SessionList.jsx
    MessageList.jsx
    MessageBubble.jsx
    ChatComposer.jsx
    CitationList.jsx
    SourceDrawer.jsx
    ToolTrace.jsx
    useAgentStream.js
```

Replace the production Chainlit mount requirement with:

```text
FastAPI backend
  -> Provides /api/agent/* for native React chat
  -> Optionally mounts Chainlit under a dev-only route during migration
```

This keeps the repository aligned with the clean-monolith goal: Chainlit informs the migration, but the product owns its own UI and contracts.

## References

- Chainlit FastAPI integration: https://docs.chainlit.io/integrations/fastapi
- Chainlit authentication overview: https://docs.chainlit.io/authentication/overview
- Chainlit customization overview: https://docs.chainlit.io/customisation/overview
- Chainlit streaming docs: https://docs.chainlit.io/advanced-features/streaming
- Chainlit data persistence overview: https://docs.chainlit.io/data-persistence/overview
- Chainlit message concept: https://docs.chainlit.io/concepts/message
- Chainlit step concept: https://docs.chainlit.io/concepts/step
- Chainlit repository: https://github.com/Chainlit/chainlit
- Chainlit frontend source: https://github.com/Chainlit/chainlit/tree/main/frontend
- Chainlit React client package: https://github.com/Chainlit/chainlit/tree/main/libs/react-client
