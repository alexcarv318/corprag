# AWS Deployment Proposal

Status: updated after the `corporate-rag` refactor as of 2026-06-15.

This plan covers production deployment and operations for `corporate-rag`. It
keeps the already deployed Neo4j Enterprise database unchanged, and introduces
repo-managed AWS infrastructure for the frontend, backend, Postgres, agent
runtime, MCP services, document storage, logging, alarms, and deployment
process.

## Goals

- Serve 50-100 simultaneous users in a stable way.
- Keep public delivery, API traffic, agent traffic, MCP tools, persistence, and
  graph access separated enough that one runtime problem does not take down the
  whole product.
- Manage infrastructure from this repository so both maintainers can review,
  change, deploy, and audit it through normal pull requests.
- Preserve the existing Neo4j deployment created from the Neo4j AWS
  CloudFormation guide:
  <https://neo4j.com/developer/kb/deploy-aws-cloudformation/>
- Make deployment and rollback repeatable.

## Current Application Shape

The refactored product currently contains:

- React/Vite frontend in `apps/web`.
- FastAPI application in `src/corporate_rag/app/main.py`.
- Protected REST API under `/api`.
- Health endpoint at `/health`.
- Native React agent integration under `/api/agent/*`.
- Chainlit runtime mounted by FastAPI at `/agent-runtime`.
- PostgreSQL persistence through `CORPORATE_RAG_DATABASE_URL`.
- Alembic migrations in `alembic/versions`.
- Corporate and law graph access through the existing Neo4j instance.
- Corporate MCP server entrypoint: `corporate-rag-corporate-mcp`.
- Law MCP server entrypoint: `corporate-rag-law-mcp`.
- Local compose services for Postgres, Neo4j, the app, and two Neo4j Cypher MCP
  servers.

The production deployment should not copy local Docker Compose exactly. Compose
is useful for development; production should split services at AWS boundaries
where scaling, health checks, security, and deployments need independence.

## Target AWS Architecture

```text
Users
  -> Route 53
  -> CloudFront
  -> AWS WAF
  -> S3 static frontend assets
  -> ALB HTTPS origin for dynamic routes

Dynamic routes
  -> ECS Fargate service: corporate-rag-api
  -> ECS Fargate service: corporate-rag-agent-runtime

Private internal services
  -> ECS Fargate service: corporate-rag-mcp-corporate
  -> ECS Fargate service: corporate-rag-mcp-law
  -> optional ECS worker service/tasks: corporate-rag-worker

Persistence
  -> Amazon RDS PostgreSQL
  -> existing Neo4j Enterprise on EC2 from the current CloudFormation deployment
  -> S3 document, artifact, and backup buckets

Operations
  -> ECR container repositories
  -> Secrets Manager
  -> CloudWatch Logs, Metrics, Dashboards, Alarms
  -> SSM Session Manager
  -> CDK stacks managed from this repository
```

## Existing AWS Inventory

Read-only audit context:

- AWS account: `110266626277`.
- Read-only identity used for inspection: `arn:aws:iam::110266626277:user/agents-mcp`.
- The configured MCP profile points at `us-east-1`, but the current corporate
  deployment footprint is in `eu-central-1`.
- `us-east-1` currently has no relevant EC2, ECS, RDS, CloudFormation, ECR,
  Secrets Manager, or CloudWatch Logs resources.

Relevant `eu-central-1` resources:

- Existing Neo4j CloudFormation stack: `acer-neo4j`.
- Existing Neo4j EC2 instance: `i-0928753bbd0a9da89`, `r8i.large`, running.
- Existing Neo4j VPC: `vpc-0a2ced7b6b9d012a7`, CIDR `10.0.0.0/16`.
- Existing Neo4j NLB:
  `acer-neo4j-nlb-668d9ea09fc11f62.elb.eu-central-1.amazonaws.com`.
- Neo4j stack output URI:
  `neo4j://acer-neo4j-nlb-668d9ea09fc11f62.elb.eu-central-1.amazonaws.com:7687`.
- Current app VPC: `acer-vpc`, `vpc-0cd0185a27d660cab`, CIDR `10.20.0.0/16`.
- Current app private subnets:
  `subnet-0a9098d819e307ad8` and `subnet-0f84d1631f99b6aa4`.
- Current app public subnets:
  `subnet-02ae454bf941573ab` and `subnet-02b7cca3d58f20370`.
- Existing public ALB: `acer-alb`, DNS
  `acer-alb-832281264.eu-central-1.elb.amazonaws.com`.
- Existing ALB host rule: `corprag.lexrag.com` forwards to
  `acer-tg-knowledge`.
- `acer-tg-knowledge` currently has one healthy target:
  `172.31.33.49:8088`.
- That target is the running EC2 instance `corpner-workflows`
  (`i-0bdff44a99647e660`) in the default VPC `vpc-0c95d26b08b168a80`.
- Existing RDS Postgres instances:
  `acer-db` and `acer-db-staging`, both `db.t3.micro`, non-public,
  single-AZ, in `acer-vpc`.
- Existing ECS clusters:
  `acer-bcknd-cluster` and `acer-rtrvr-cluster`.
- Existing ECS services are present but all inspected services have
  `desiredCount=0`.
- Existing Acer ECR repositories:
  `acer/backend`, `acer/backend-staging`, `acer/celery`,
  `acer/celery-staging`, `acer/flower`, `acer/flower-staging`,
  `acer/retriever`, `acer/retriever-staging`.
- Existing Acer S3 buckets in `eu-central-1`:
  `acer-app-assets-prod`, `acer-backups-prod`, `acer-logs-prod`,
  `acer-user-avatars-prod`, `acer-user-documents-prod`.
- These Acer buckets have public access blocked and versioning enabled.
- Existing ACM certificate for `lexrag.com` in `eu-central-1` is issued.
- No regional WAF Web ACL was found in `eu-central-1`; no CloudFront WAF Web ACL
  was found in `us-east-1`.

Important security observations:

- The Neo4j CloudFormation stack created an internet-facing NLB.
- The Neo4j external security group currently allows `0.0.0.0/0` ingress to
  SSH `22`, HTTP `7474`, and Bolt `7687`.
- The old `corpner-workflows` instance is public through ALB on
  `corprag.lexrag.com` and also has a security group allowing public ingress to
  `80`, `8088`, and `22`.
- The current `acer-vpc` has a NAT gateway and an S3 VPC endpoint.
- There is VPC peering between `acer-vpc` (`10.20.0.0/16`) and the default VPC
  (`172.31.0.0/16`), but no observed private peering between `acer-vpc` and the
  Neo4j VPC (`10.0.0.0/16`).

## Integration With Existing AWS

Deploy `corporate-rag` in `eu-central-1` unless there is a deliberate decision
to move the graph and application to another region. Deploying in `us-east-1`
would add unnecessary cross-region latency to Neo4j and would not reuse the
current Acer operational footprint.

Recommended integration path:

1. Use `acer-vpc` (`vpc-0cd0185a27d660cab`) for the first production ECS/RDS
   deployment, but define the new `corporate-rag` ECS services, target groups,
   ECR repositories, log groups, secrets, and alarms in CDK.
2. Keep the existing `acer-neo4j` CloudFormation stack imported by reference.
   Do not recreate or adopt the Neo4j resources into CDK.
3. Configure `CORPORATE_RAG_NEO4J_URI` from the existing Neo4j stack output:
   `neo4j://acer-neo4j-nlb-668d9ea09fc11f62.elb.eu-central-1.amazonaws.com:7687`.
4. Store Neo4j credentials in Secrets Manager and inject them into ECS tasks.
5. Create new target groups for:
   - `corporate-rag-api`
   - `corporate-rag-agent-runtime`
6. Add ALB listener rules for the new deployment. Use one of these cutover
   strategies:
   - Conservative: add `corporate-rag-staging.lexrag.com` first, test the full
     app there, then move `corprag.lexrag.com` from `acer-tg-knowledge` to the
     new CloudFront/ALB path.
   - Direct: replace the existing `corprag.lexrag.com` rule only after the ECS
     services pass smoke tests.
7. Prefer CloudFront in front of S3 and ALB for the final production shape. The
   existing `acer-alb` can remain the ALB origin.
8. Use new ECR repositories named `corporate-rag/*` or
   `corporate-rag-<service>` instead of pushing the refactored app into the old
   `acer/backend` repositories.
9. Use new log groups under `/corporate-rag/prod/*` instead of the old
   `/ecs/acer/*` groups.
10. Use new Secrets Manager names under `/corporate-rag/prod/*` or
    `corporate-rag/prod/*` instead of mixing new app secrets into `acer/*`.
11. Create a new RDS database instance or database/schema for `corporate-rag`.
    The existing `acer-db` is `db.t3.micro`, single-AZ, and should not be the
    final production database for 50-100 simultaneous users.
12. Keep `corpner-workflows` running during validation. Retire it only after the
    new ECS deployment is healthy, DNS/ALB cutover is complete, and rollback has
    been rehearsed.

Preferred Neo4j networking improvement:

- Short term: ECS tasks can connect to the existing public Neo4j NLB, but this
  keeps the graph exposed more broadly than desired.
- Better production target: establish private connectivity between `acer-vpc`
  and the Neo4j VPC, then restrict Neo4j Bolt access to the new
  `corporate-rag` ECS security groups and approved admin access.
- If the CloudFormation template makes that difficult, keep the Neo4j stack
  unchanged but add the narrowest possible security-group and CIDR restrictions
  around the NLB/instance.

Do not reuse the old default VPC deployment pattern for the new product. The
default VPC currently hosts the legacy `corpner-workflows` instance and many
stopped ingestion/completeness EC2 instances. New app services should run in the
managed `acer-vpc` private subnets or in a new CDK-managed VPC with explicit
private connectivity to Neo4j.

## Repository Infrastructure Layout

Create a root infrastructure folder:

```text
corporate-rag/
├── infra/
│   ├── README.md
│   ├── pyproject.toml
│   ├── cdk.json
│   ├── app.py
│   ├── corporate_rag_infra/
│   │   ├── config.py
│   │   ├── network_stack.py
│   │   ├── storage_stack.py
│   │   ├── database_stack.py
│   │   ├── compute_stack.py
│   │   ├── observability_stack.py
│   │   └── pipeline_stack.py
│   ├── config/
│   │   ├── dev.yaml
│   │   ├── staging.yaml
│   │   └── prod.yaml
│   └── runbooks/
│       ├── deploy.md
│       ├── rollback.md
│       ├── rotate-secrets.md
│       ├── postgres-restore.md
│       ├── neo4j-backup-restore.md
│       └── incident-response.md
```

Use AWS CDK in Python. This matches the backend language and keeps the
infrastructure easy for a Python-focused maintainer to read. Terraform is also a
valid choice, but do not mix both for the same environment.

Infrastructure rules:

- All durable AWS resources are defined in CDK except the existing Neo4j stack.
- Environment differences live in `infra/config/*.yaml`, not hard-coded stack
  branches.
- Production changes go through pull requests.
- `cdk diff` output is reviewed before `cdk deploy`.
- CDK bootstrap and deploy permissions are documented in `infra/README.md`.
- Generated files, local CDK context churn, and credentials are not committed.
- Neo4j connection details are imported as config and secrets, not managed as a
  CDK-created database.

## AWS Accounts And Environments

Recommended environments:

- `dev`: low-cost sandbox for infrastructure changes.
- `staging`: production-like smoke and migration rehearsal.
- `prod`: client-facing deployment.

Use separate AWS accounts if possible. If one account must be used initially,
use separate VPCs, stacks, names, secrets, and KMS keys per environment.

Tag every resource with:

- `Application=corporate-rag`
- `Environment=dev|staging|prod`
- `ManagedBy=cdk`
- `Owner=<team-or-maintainer>`

## Networking

Use one VPC per environment:

- 2 or 3 Availability Zones.
- Public subnets for ALB and NAT gateways.
- Private application subnets for ECS services.
- Isolated or private database subnets for RDS.
- VPC endpoints for S3, ECR, CloudWatch Logs, Secrets Manager, and SSM where
  cost and routing justify them.

Security group model:

- CloudFront reaches the public ALB only over HTTPS.
- ALB reaches API and agent ECS tasks on their container ports.
- API and agent tasks reach RDS PostgreSQL.
- API, agent, MCP, and worker tasks reach the existing Neo4j security group on
  Bolt only.
- Agent tasks reach MCP services through private service discovery.
- MCP services have no public ingress.
- S3 buckets are private; app access is through IAM roles and signed URLs when
  needed.

## Frontend

Deploy `apps/web` as static assets:

- Build with `npm ci && npm run build`.
- Upload `apps/web/dist` to a private S3 bucket.
- Serve through CloudFront.
- Route unknown frontend paths to `index.html`.
- Cache hashed assets aggressively.
- Keep `index.html` on a short TTL or invalidate it on each deploy.

CloudFront routing:

- Static frontend: S3 origin.
- `/api/*`: ALB origin to `corporate-rag-api`.
- `/health`: ALB origin to `corporate-rag-api`.
- `/agent-runtime/*`: ALB origin to `corporate-rag-agent-runtime`.
- WebSocket forwarding must be enabled for `/agent-runtime/ws/socket.io`.

The frontend should use same-origin API calls in production. Avoid baking an
environment-specific API hostname into the bundle unless there is a clear need.

## Backend API Service

Deploy FastAPI as `corporate-rag-api` on ECS Fargate.

Responsibilities:

- `/health`
- `/api/auth/*`
- `/api/workflows/*`
- `/api/typeahead/*`
- `/api/facets/*`
- `/api/evidence/*`
- `/api/documents/*`
- `/api/agent/config`
- `/api/agent/handoff`

Initial sizing for 50-100 users:

- Desired tasks: `2`
- Minimum tasks: `2`
- Maximum tasks: `6`
- CPU: `1 vCPU` per task
- Memory: `2 GB` per task to start
- Uvicorn workers: start with `1` per task unless load testing shows CPU-bound
  request handling; scale tasks before multiplying workers.

Autoscaling signals:

- ALB request count per target.
- CPU above 60-70%.
- Memory above 70%.
- p95 latency.
- 5xx rate.

Production requirements:

- API tasks are stateless.
- Auth state, users, and sessions live in RDS PostgreSQL.
- Graph access goes through the Neo4j driver with bounded connection pools.
- All required settings come from task environment and Secrets Manager.
- The task role can read only the secrets and buckets needed by the API.
- Alembic migrations are not run automatically by every API task.
- ALB/ECS health checks need an unauthenticated liveness endpoint. The current
  app protects `/health` through the shared auth dependency, so add a dedicated
  public liveness path or make `/health` safe for unauthenticated infrastructure
  checks before production deployment.

## Agent Runtime Service

Deploy Chainlit/agent runtime as `corporate-rag-agent-runtime` on ECS Fargate.

The current application mounts Chainlit inside FastAPI at `/agent-runtime`.
Production should still use a separate ECS service for this runtime, even if it
uses the same Python package and Dockerfile at first.

Responsibilities:

- `/agent-runtime/*`
- Chainlit header-auth callback and WebSocket sessions.
- LLM streaming.
- Agent session lifecycle.
- Tool event streaming.
- Corporate and law agent mode execution.

Initial sizing:

- Desired tasks: `2`
- Minimum tasks: `2`
- Maximum tasks: `8`
- CPU: `1-2 vCPU` per task
- Memory: `4 GB` per task

Why separate from the API:

- Agent calls are long-running and bursty.
- LLM and tool latency should not consume normal workflow API capacity.
- Agent prompt/tool fixes should be deployable without touching the API.
- Agent autoscaling and alarms are different from API traffic.

Session persistence:

- Chainlit data is persisted in PostgreSQL through
  `CORPORATE_RAG_DATABASE_URL`.
- The `threads`, `steps`, `elements`, and `feedbacks` tables are created by
  Alembic migrations.
- Do not depend on in-memory task-local session state for anything that must
  survive scaling or task replacement.

WebSocket requirements:

- ALB idle timeout should be raised for agent streaming.
- CloudFront and ALB must forward WebSocket upgrade headers for
  `/agent-runtime/ws/socket.io`.
- Sticky sessions can be enabled for the agent target group if Chainlit requires
  it during testing, but the preferred target is durable/shared session state
  rather than task affinity.

## MCP Services

Run MCP as private internal services, not hidden subprocesses inside the public
web runtime.

Services:

- `corporate-rag-mcp-corporate`
- `corporate-rag-mcp-law`

Use one of these implementation choices:

- Preferred: package-native MCP entrypoints from this repository:
  `corporate-rag-corporate-mcp` and `corporate-rag-law-mcp`.
- Acceptable interim option: the same `mcp/neo4j-cypher` images currently used
  in `docker-compose.yml`, one configured for database `neo4j` and one for
  database `law`.

Networking:

- Private subnets only.
- No public ALB listener.
- Cloud Map service discovery or an internal ALB.
- Only the agent service and approved admin/worker tasks can call MCP services.

Initial sizing:

- Desired tasks: `2` per MCP service for production.
- CPU: `0.5-1 vCPU`.
- Memory: `1-2 GB`.
- Scale with agent concurrency and observed query latency.

Operational rules:

- MCP tools remain read-only unless a separate admin mutation surface is
  explicitly designed.
- Tool contract tests run before agent deployment.
- Response token limits and Neo4j query timeouts are configured explicitly.
- MCP service logs never include secrets or full sensitive document text.

## PostgreSQL

Use Amazon RDS PostgreSQL for application persistence.

Current persisted data:

- Product users in `users`.
- Chainlit threads in `threads`.
- Chainlit steps in `steps`.
- Chainlit elements in `elements`.
- Chainlit feedback in `feedbacks`.

Initial production configuration:

- Engine: RDS PostgreSQL.
- Deployment: Multi-AZ DB instance for production.
- Instance class: start with a burstable or general-purpose class sized around
  `2 vCPU / 4-8 GB RAM`, then tune after load testing.
- Storage: gp3, encrypted with KMS, autoscaling enabled.
- Backups: 7-14 days retention for staging, 30 days for production.
- Deletion protection: enabled for production.
- Public access: disabled.
- Access: only ECS task security groups and approved admin paths.

Connection management:

- Start with app pool settings from `DatabaseSettings`:
  `CORPORATE_RAG_DATABASE_POOL_MIN_SIZE=1`,
  `CORPORATE_RAG_DATABASE_POOL_MAX_SIZE=5`.
- With 2 API tasks and 2 agent tasks, this keeps initial connection usage
  modest.
- Add RDS Proxy if task count or Chainlit concurrency makes direct connections
  noisy.

Migrations:

- Run `alembic upgrade head` as a one-off ECS task or CI/CD deployment step.
- Migration execution must be explicit and visible in deployment logs.
- Rehearse migrations in staging before production.
- Never have every application task auto-run migrations on startup.

## Existing Neo4j

The existing Neo4j Enterprise deployment remains untouched.

Production requirements around it:

- Do not recreate it in the new CDK stacks.
- Import its Bolt URI, security group, database names, and credentials into the
  app configuration.
- Keep current database names:
  - corporate graph: `neo4j`
  - law graph: `law`
- Keep Neo4j private; no public Bolt or browser access.
- Access it from ECS through security groups, not IP allowlists.
- Store credentials in Secrets Manager.
- Use SSM Session Manager for EC2 administration.
- Keep required plugins and imports compatible with the existing deployment.

Application controls:

- Configure Neo4j driver connection lifetimes and acquisition timeouts through
  `CORPORATE_RAG_NEO4J_*` settings.
- Set query timeouts in repository/client code where supported.
- Limit per-service connection pools to protect Neo4j from API, agent, MCP, and
  worker fan-out.
- Treat Neo4j as the main scaling bottleneck until measured otherwise.

Operations:

- Daily Neo4j dumps to S3.
- EBS snapshots before graph migrations or major imports.
- Restore drill before real client usage.
- CloudWatch alarms for instance status, CPU, memory pressure, and disk usage.
- Separate runbook in `infra/runbooks/neo4j-backup-restore.md`.

## Document And Artifact Storage

Use private S3 buckets:

- `corporate-rag-<env>-frontend-assets`
- `corporate-rag-<env>-documents`
- `corporate-rag-<env>-artifacts`
- `corporate-rag-<env>-neo4j-backups`
- `corporate-rag-<env>-logs-archive` if long-term log export is required

Rules:

- Block public access.
- Encrypt with KMS.
- Version important buckets.
- Use lifecycle policies for temporary artifacts.
- Use signed URLs only where browser upload/download needs direct S3 access.
- Separate original uploads, normalized artifacts, and generated reports by
  prefix.

## Ingestion And Background Work

Do not run heavy ingestion inside the API or agent runtime.

Recommended production shape:

```text
Upload document to S3
  -> create ingestion record/job
  -> push message to SQS
  -> ECS worker consumes job
  -> worker writes graph updates to Neo4j
  -> worker writes artifacts/reports to S3
  -> worker records status in PostgreSQL
```

Phase-1 shape:

- Admin-only one-off ECS tasks are acceptable.
- No client-facing ingestion until quality, rollback, and restore behavior are
  proven.
- Worker code should use the same application settings and secrets model as the
  API.

When ingestion becomes active:

- Add an SQS queue and dead-letter queue.
- Add CloudWatch alarms for failed jobs and DLQ depth.
- Add idempotency keys for ingestion jobs.
- Add graph migration/import runbooks.

## Secrets And Configuration

Use AWS Secrets Manager for:

- `CORPORATE_RAG_DATABASE_URL` or separate RDS username/password components.
- `CORPORATE_RAG_AUTH_SECRET_KEY`.
- `CORPORATE_RAG_AUTH_SIGNUP_KEY`.
- `CORPORATE_RAG_AGENT_OPENAI_API_KEY`.
- `CHAINLIT_AUTH_SECRET` if not derived from auth secret.
- Neo4j URI, username, password, and database names.
- Deployment webhooks or CI tokens if needed.

Use plain ECS environment variables for non-secret config:

- `CORPORATE_RAG_ENVIRONMENT=prod`
- `CORPORATE_RAG_LOG_LEVEL=INFO`
- `CORPORATE_RAG_API_PREFIX=/api`
- `CORPORATE_RAG_AGENT_CHAINLIT_MOUNT_PATH=/agent-runtime`
- `CORPORATE_RAG_AGENT_SECURE_HANDOFF_COOKIE=true`
- MCP transport and private service URLs.

Rules:

- No secrets in committed `.env` files.
- No secrets in Docker images.
- No plaintext secrets in task definitions.
- No secrets or document text in logs.
- Task roles read only the secrets needed by that specific service.

## Logging, Metrics, And Alarms

Use CloudWatch Logs for all ECS services.

Required log groups:

- `/corporate-rag/<env>/api`
- `/corporate-rag/<env>/agent-runtime`
- `/corporate-rag/<env>/mcp-corporate`
- `/corporate-rag/<env>/mcp-law`
- `/corporate-rag/<env>/worker`
- `/corporate-rag/<env>/migrations`

Logging requirements:

- JSON structured logs.
- Request id on every API request.
- User id where safe.
- Workflow id where relevant.
- Agent session/thread id where relevant.
- MCP tool name and duration.
- LLM model id, latency, and error status.
- No secrets.
- No full sensitive document text.

Required dashboards:

- API request count, p50/p95/p99 latency, 4xx, 5xx.
- Agent active connections, message count, latency, LLM errors.
- ECS task count, CPU, memory, restarts.
- RDS CPU, storage, connections, read/write latency.
- Neo4j EC2 CPU, disk, status checks, backup status.
- MCP request count, latency, errors.
- SQS queue depth and DLQ depth when workers are enabled.

Required alarms:

- ALB 5xx rate.
- API p95 latency above threshold.
- Agent p95 latency or WebSocket failure spike.
- ECS task restart loop.
- High ECS CPU or memory.
- RDS high CPU, storage low, connections high.
- Neo4j disk usage high.
- Neo4j instance status check failed.
- Backup failure.
- Ingestion DLQ not empty.
- LLM provider error spike.
- LLM cost or token spike.

## Security

Public surface:

- CloudFront.
- WAF.
- ALB HTTPS routes for `/api/*`, `/health`, and `/agent-runtime/*`.

Private surface:

- ECS services.
- MCP services.
- RDS PostgreSQL.
- Existing Neo4j EC2.
- S3 buckets.
- Secrets Manager.

Minimum controls:

- HTTPS only.
- WAF managed rules and rate limiting.
- Strong auth secret.
- Signup key disabled or tightly controlled after initial account bootstrap.
- Secure handoff cookie in production.
- Least-privilege IAM per ECS task.
- Private subnets for runtime services.
- No public Neo4j.
- No public RDS.
- CloudTrail enabled for account audit.
- GuardDuty enabled where budget permits.

## Container Images

Use ECR repositories:

- `corporate-rag-api`
- `corporate-rag-agent-runtime`
- `corporate-rag-mcp-corporate`
- `corporate-rag-mcp-law`
- `corporate-rag-worker` when needed

At first these can be built from the same Python package and Dockerfile with
different commands. Split Dockerfiles only when build size or dependencies make
that worthwhile.

Recommended commands:

- API: `corporate-rag serve --host 0.0.0.0 --port 8088` with Chainlit mounting
  disabled or routed only if the code has a runtime flag for it.
- Agent runtime: same app package serving `/agent-runtime`, or a small app
  factory dedicated to Chainlit if introduced later.
- Corporate MCP: `corporate-rag-corporate-mcp --transport streamable-http`.
- Law MCP: `corporate-rag-law-mcp --transport streamable-http`.

Implementation note: the current app always mounts Chainlit. Before production,
add a small configuration switch or separate app factory so the API service does
not unnecessarily start the Chainlit runtime.

## CI/CD Deployment Process

Use GitHub Actions or the team's existing CI runner.

Pipeline:

1. Install backend dependencies.
2. Run `ruff check .`.
3. Run `mypy`.
4. Run `pytest`.
5. Install frontend dependencies with `npm ci` in `apps/web`.
6. Run frontend lint.
7. Build frontend.
8. Build Docker images.
9. Push images to ECR with immutable git SHA tags.
10. Run `cdk diff` for the target environment.
11. Deploy infrastructure changes with CDK after approval.
12. Run Alembic migrations as a one-off ECS task.
13. Deploy ECS services with rolling deployments.
14. Upload frontend assets to S3 and invalidate CloudFront.
15. Run smoke tests.

Smoke tests:

- Unauthenticated infrastructure health check path.
- Auth sign-in with a test account.
- `GET /api/workflows/catalog`.
- One safe workflow execution.
- `GET /api/agent/config`.
- Agent handoff creation.
- `/agent-runtime` startup.
- Corporate MCP tool list.
- Law MCP tool list.

Rollback:

- Frontend: redeploy previous asset version or revert CloudFront/S3 deployment
  metadata.
- API/agent/MCP: redeploy previous ECR git SHA tag.
- Migrations: do not auto-rollback production data. Use an explicit migration
  rollback or restore runbook.
- Neo4j: never auto-rollback data. Use the documented restore procedure.

## Infrastructure Management By Two Maintainers

Both maintainers should be able to operate the system without sharing personal
credentials.

Access model:

- Use AWS IAM Identity Center or separate IAM users/roles.
- Give both maintainers read access to production and deploy access through an
  assumed role.
- Avoid long-lived admin keys on laptops.
- Require MFA.
- Keep break-glass admin access documented and rarely used.

Repository process:

- Infrastructure changes are pull requests under `infra/`.
- Each PR includes `cdk diff` output or a summary of changed AWS resources.
- Production deploys require approval from the second maintainer when practical.
- Runbooks live beside the CDK code.
- Environment config is reviewed like application config.

Operational habits:

- Weekly review of alarms, costs, failed backups, and ECS task restarts.
- Monthly restore drill for Postgres in staging.
- Scheduled Neo4j restore drill before any serious client usage.
- Secret rotation calendar for auth, database, Neo4j, and LLM provider keys.
- Dependency update cadence for both backend and frontend.

## Recommended Phase-1 Build

Build this first:

```text
infra/ CDK foundation
Route 53 + ACM + CloudFront + WAF
S3 frontend asset bucket
ALB
ECS service: corporate-rag-api
ECS service: corporate-rag-agent-runtime
ECS services: corporate-rag-mcp-corporate and corporate-rag-mcp-law
RDS PostgreSQL
Secrets Manager
S3 documents/artifacts/backups
CloudWatch logs, dashboard, and alarms
Existing Neo4j EC2 connected by security group
CI/CD pipeline with migrations and smoke tests
```

Before production launch:

- Add a runtime switch or separate app factory so the API service and agent
  service can be deployed independently.
- Confirm CloudFront and ALB WebSocket behavior for Chainlit.
- Load test 50-100 simultaneous users with a realistic mix of workflow and
  agent traffic.
- Tune Neo4j driver pools and query timeouts.
- Rehearse Postgres restore.
- Rehearse Neo4j backup restore.
- Confirm all alarms page the right people or notify the right channel.

Do not deploy the production system as one monolithic Fargate service. That is
acceptable for local development, but it is weak for production operations,
agent scaling, deploy speed, and failure isolation.

## Cost Comparison

Cost Explorer snapshot captured on 2026-06-15 with the read-only
`codex-readonly` AWS profile:

- Account: `110266626277`.
- June 2026 month-to-date, 2026-06-01 through 2026-06-16:
  `$465.90`.
- June 2026 month-to-date excluding tax: `$427.43`.
- AWS June 2026 forecast: `$962.49`.
- May 2026 finalized total: `$1,089.68`.

Current June 2026 month-to-date cost by largest service:

| Service | Cost |
| --- | ---: |
| EC2 - Other | `$125.51` |
| EC2 Compute | `$123.82` |
| ECS | `$59.54` |
| Tax | `$38.47` |
| RDS | `$33.23` |
| VPC | `$32.56` |
| Load Balancing | `$26.58` |
| ECR | `$9.40` |
| WorkMail | `$9.31` |
| Secrets Manager | `$4.88` |
| Route 53 | `$1.50` |
| CloudWatch | `$0.66` |
| S3 | `$0.39` |

Current June 2026 month-to-date cost by largest region:

| Region | Cost |
| --- | ---: |
| `ap-southeast-1` | `$210.36` |
| `eu-central-1` | `$203.83` |
| Tax / no region | `$38.47` |
| `eu-west-1` | `$10.08` |
| Global | `$1.50` |

The proposed `corporate-rag` production baseline in `eu-central-1`, excluding
LLM provider usage and taxes, is expected to add or replace roughly:

| Area | Estimated Monthly Cost |
| --- | ---: |
| ECS Fargate: API, agent runtime, MCP services | `$265-$335` |
| RDS PostgreSQL Multi-AZ `db.t4g.medium`, storage, backups | `$125-$150` |
| ALB and light LCU usage | `$25-$45` |
| NAT gateway | `$0 incremental if reusing existing acer-vpc NAT`; otherwise `$35-$85` |
| CloudFront and S3 frontend/document/artifact storage | `$10-$40` |
| WAF | `$15-$35` |
| CloudWatch logs, alarms, dashboards | `$20-$70` |
| Secrets Manager | `$5-$15` |
| ECR, Route 53, SQS, and miscellaneous | `$5-$25` |

Expected new production run-rate:

- New `corporate-rag` infrastructure: about `$470-$715/month`.
- If agent/API/MCP services scale toward their configured maximums:
  about `$1,100-$1,600/month`.
- Existing Neo4j dependency, counted separately because it remains untouched:
  about `$165-$220/month`.
- Baseline total including existing Neo4j:
  about `$635-$935/month`.

Interpretation:

- The proposed baseline is in the same order as the current account run-rate,
  but it replaces the fragile legacy `corpner-workflows` EC2 shape with
  distributed ECS/RDS/CloudFront operations.
- The current account has costs outside the corporate deployment, especially in
  `ap-southeast-1` for Lexrag/Locram resources. Do not compare the proposed
  `corporate-rag` baseline directly to the whole account bill without excluding
  unrelated products.
- Cleanup after cutover should reduce the legacy `eu-central-1` EC2, EBS, ECR,
  ALB target group, idle ECS, and public IPv4 costs. This should partially
  offset the new ECS/RDS production services.
- The largest variable not shown here is LLM/API-provider spend. Agent traffic
  and model choice can exceed AWS infrastructure cost if usage is heavy.

## Existing AWS Cleanup After Cutover

Cleanup must happen after the new `corporate-rag` deployment is live, smoke
tested, backed up, and rollback-tested. Do not delete or mutate the existing
Neo4j CloudFormation stack as part of this cleanup.

Keep:

- CloudFormation stack `acer-neo4j`.
- Running Neo4j EC2 instance `i-0928753bbd0a9da89`.
- Neo4j EBS volume attached to `i-0928753bbd0a9da89`.
- Neo4j NLB and target groups until private connectivity is proven.
- Neo4j credentials and backup secrets required by the graph.
- Any S3 backup bucket/prefix that contains Neo4j dumps or graph restore
  artifacts.

Clean up or replace after `corporate-rag` cutover:

- Retire `corpner-workflows` EC2 instance `i-0bdff44a99647e660` after
  `corprag.lexrag.com` no longer points to `acer-tg-knowledge`.
- Remove `172.31.33.49:8088` from `acer-tg-knowledge` after DNS/ALB cutover.
- Delete the `acer-tg-knowledge` target group if it has no remaining purpose.
- Remove the `corprag.lexrag.com` ALB listener rule only if CloudFront owns that
  hostname directly; otherwise repoint the rule to the new ECS target group.
- Review and terminate stopped one-off ingestion/completeness EC2 instances in
  the default VPC after confirming their EBS volumes contain no unique data:
  `acer-ingestion-01` through `acer-ingestion-05`,
  `acer-ingestion-server`, and `corpner-completeness-01` through
  `corpner-completeness-05`.
- Review stopped `acer-retrieval` EC2 and its Elastic IP
  `63.181.51.154`; release the EIP if the server is no longer needed.
- Review stopped `acer-inference`, `acer-valkey`, and the older private
  `acer-neo4j` instance in `acer-vpc`; keep only if they are part of a current
  ingestion or retrieval workflow.
- Remove or scale down old ECS services with `desiredCount=0` once their task
  definitions, target groups, and ECR images are no longer needed:
  `acer-backend-service`, `acer-backend-service-staging`,
  `acer-celery-service`, `acer-celery-service-staging`,
  `acer-flower-service`, `acer-flower-service-staging`,
  `acer-retriever-service`, and `acer-retriever-service-staging`.
- Delete stale ALB target groups with no registered targets after confirming no
  listener rule depends on them:
  `acer-tg-backend`, `acer-tg-backend-stg`, `acer-tg-flower`,
  `acer-tg-flower-stg`, and `acer-tg-retriever-stg`.
- Remove old ECR repositories only after their image tags are no longer a
  rollback source: `acer/backend`, `acer/backend-staging`, `acer/celery`,
  `acer/celery-staging`, `acer/flower`, `acer/flower-staging`,
  `acer/retriever`, and `acer/retriever-staging`.
- Review old CloudWatch log groups under `/ecs/acer/*`; export anything needed
  for audit, then delete or set retention.
- Review CloudWatch alarms in `INSUFFICIENT_DATA` that target retired ECS
  services or stale target groups; delete or replace them with
  `/corporate-rag/prod/*` alarms.
- Review old Amplify test stacks and Lambda functions in `eu-central-1`
  (`amplify-testapp-staging-*`, `amplify-login-*`) and delete them if they are
  unrelated to active products.
- Review old standalone secrets in `eu-west-1`:
  `ainsdb_credentials`, `secret_key`, and `s3_secret_key`.
- Keep Lexrag and Locram resources in `ap-southeast-1` separate unless there is
  a deliberate cross-product consolidation project.

Security cleanup priorities:

1. Remove public SSH `0.0.0.0/0` from Neo4j external security group
   `sg-0e88572f9dd5336bf`; use SSM Session Manager or tightly allowlisted
   access instead.
2. Restrict public Neo4j HTTP `7474` and Bolt `7687` ingress. The target state
   is private app-to-graph access only.
3. Remove public SSH from `acer-ingestion-sg` and other old EC2 security groups
   before leaving any old instance running.
4. Ensure the new `corporate-rag` ECS services use private subnets with no
   public IP assignment.
5. Replace broad legacy IAM roles with least-privilege `corporate-rag` task
   roles before retiring old deploy roles.

Cleanup process:

1. Create final snapshots/backups for any EC2 volume, RDS database, or S3 prefix
   that may contain unique data.
2. Record each cleanup candidate in an issue or checklist with owner, date, and
   rollback decision.
3. Disable or scale to zero first where possible.
4. Wait through one normal business cycle.
5. Delete resources only after logs, backups, and rollback requirements are
   satisfied.
6. Update `infra/runbooks/rollback.md` so it no longer references removed
   resources.
