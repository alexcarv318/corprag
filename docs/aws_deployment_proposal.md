# AWS Deployment Proposal

## Goal

Production deployment for `corporate-rag` that can serve 50-100 users from different countries without putting the whole product into one fragile runtime.

The deployment must be easy to operate, easy to redeploy, and safe to scale.

## High-Level Shape

```text
Users
  -> Route 53
  -> CloudFront
  -> AWS WAF
  -> S3 frontend bucket for React static assets
  -> ALB for dynamic backend traffic

Backend
  -> ECS Fargate service: corporate-rag-api
  -> ECS Fargate service: corporate-rag-agent
  -> ECS Fargate service or tasks: MCP servers
  -> existing Neo4j Enterprise on EC2

Operations
  -> ECR for container images
  -> Secrets Manager for secrets
  -> S3 for documents, artifacts, backups
  -> CloudWatch for logs, metrics, alarms
  -> SSM for EC2 access and operational commands
```

## Frontend

Deploy the React/Vite frontend as static assets:

- Build in CI.
- Upload build output to an S3 static assets bucket.
- Serve through CloudFront.
- Cache hashed assets aggressively.
- Keep `index.html` on short TTL for fast rollbacks.

This keeps frontend delivery cheap, global, and independent from backend scaling.

## Backend API

Deploy FastAPI as its own ECS Fargate service: `corporate-rag-api`.

Responsibilities:

- `/api/*`
- `/health`
- workflow catalog and workflow execution
- document source APIs
- auth/session APIs
- lightweight admin APIs

Initial sizing:

- Desired tasks: `2`
- Max tasks: `4`
- CPU: `1 vCPU` per task
- Memory: `2-4 GB` per task
- Multi-AZ private subnets
- Public access only through ALB

Autoscaling signals:

- CPU
- memory
- ALB request count
- p95 latency
- 5xx rate

The API must be stateless. Any session, job, or chat state must live outside the task.

## Agent Runtime

Deploy Chainlit/agent runtime as a separate ECS Fargate service: `corporate-rag-agent`.

Responsibilities:

- `/agent/*`
- LLM session lifecycle
- tool streaming
- citation/source rendering
- agent-specific auth/session handling

Reason for separation:

- Agent requests are long-running and bursty.
- Agent latency and token usage should not affect normal workflow API traffic.
- Agent deploys should be fast and isolated.
- Agent scaling policy is different from API scaling.

Initial sizing:

- Desired tasks: `2`
- Max tasks: `6`
- CPU: `1-2 vCPU` per task
- Memory: `4 GB` per task

Required before scaling beyond one task:

- Persistent checkpointer/session store.
- No in-memory-only session state.
- Shared auth/session backing store.

Recommended backing store:

- DynamoDB or Postgres/RDS for durable agent sessions/checkpoints.
- Redis/ElastiCache only if low-latency transient coordination is needed.

## MCP Servers

Do not run MCP servers as hidden subprocesses inside the public web task in production.

Use separate internal services:

- `corporate-rag-mcp-corporate`
- `corporate-rag-mcp-law`

Runtime options:

- Preferred production: internal HTTP MCP services behind private Cloud Map service discovery.
- Acceptable phase-1 fallback: MCP sidecars inside the agent task, not inside the API task.
- Local development: stdio MCP remains supported.

Network access:

- MCP services are private only.
- No public ALB route.
- Only `corporate-rag-agent` and selected admin tasks can call them.
- Security groups restrict access by service, not by IP allowlists.

Scaling:

- Start with `1-2` tasks per MCP service.
- Scale with agent traffic if needed.
- Keep MCP tools read-only unless a separate admin mutation surface is designed.

## Neo4j

Use the existing Neo4j Enterprise deployment created through the AWS CloudFormation template.

Production requirements:

- Keep Neo4j on EC2, not Fargate.
- Keep the existing Neo4j Enterprise version line unless an explicit upgrade plan
  has been tested against the graph, plugins, and ingestion jobs.
- Place Neo4j in private subnets.
- Access from ECS services through security groups.
- Use EBS gp3.
- Use SSM Session Manager for admin access.
- No public Bolt/browser access.
- Store credentials in Secrets Manager.
- Keep required plugins available and version-compatible:
  - APOC for administrative/import/query utilities.
  - n10s/neosemantics for RDF/OWL ontology import, including FIBO.
- Validate plugin compatibility before Neo4j upgrades. APOC versioning follows
  Neo4j year/month compatibility, and n10s must be tested with the target Neo4j
  release before production use.

Operational requirements:

- Daily Neo4j dump to S3.
- EBS snapshots before migrations.
- Restore drill before real client usage.
- CloudWatch alarms for CPU, memory, disk, and instance status.
- Query timeout policy in the app.
- Driver connection pool limits per ECS service.

Neo4j is the main bottleneck. Scale app services only after Neo4j limits are measured.

Local development must mirror this shape closely enough to catch graph/runtime
issues early: same Neo4j Enterprise version line by default, APOC enabled,
`/plugins` mounted for n10s and other compatible jars, ontology imports mounted
for FIBO/RDF work, and corporate/law MCP services available through Docker
Compose.

## Documents And Storage

Use S3 buckets:

- `corporate-rag-documents`: original uploads and normalized document artifacts.
- `corporate-rag-artifacts`: frontend builds, deployment artifacts, reports.
- `corporate-rag-neo4j-backups`: dumps, snapshots metadata, restore artifacts.

S3 rules:

- Block public access.
- Encrypt with KMS.
- Use lifecycle policies for temporary artifacts.
- Use signed URLs only where needed.

## Ingestion

Do not run heavy ingestion inside API or agent services.

Production shape:

- Upload document to S3.
- Create ingestion job.
- Push job to SQS.
- Run ingestion in dedicated ECS worker tasks.
- Write results to Neo4j.
- Store receipt/report in S3.

Phase-1:

- Admin-only CLI or admin-only API.
- ECS one-off task is acceptable.
- No client-facing ingestion until quality and rollback are proven.

## Secrets

Use AWS Secrets Manager for:

- Neo4j URI, user, password.
- OpenAI/API provider keys.
- auth signing secret.
- Chainlit secret.
- admin bootstrap credentials.
- webhook/deploy tokens if needed.

Use ECS task role permissions to read only required secrets per service.

Do not store secrets in:

- `.env` committed to git
- Docker images
- CI logs
- task definitions as plaintext

## Logs, Metrics, Alarms

Use CloudWatch Logs for all ECS services.

Required log groups:

- `/corporate-rag/api`
- `/corporate-rag/agent`
- `/corporate-rag/mcp-corporate`
- `/corporate-rag/mcp-law`
- `/corporate-rag/ingestion`

Logging requirements:

- JSON structured logs.
- request id on every API request.
- user id or tenant id where safe.
- workflow id and agent session id where relevant.
- no document text or secrets in logs.

Required alarms:

- ALB 5xx rate.
- API p95 latency.
- agent p95 latency.
- ECS task restarts.
- high CPU/memory.
- Neo4j disk usage.
- Neo4j CPU/memory pressure.
- backup failure.
- ingestion failure rate.
- LLM error rate and cost spike.

## Deploy Process

Use AWS CDK in Python for infrastructure.

Use CI/CD:

1. Run tests, lint, typecheck.
2. Build frontend.
3. Upload frontend assets to S3.
4. Build backend/agent/MCP Docker images.
5. Push images to ECR with git SHA tags.
6. Deploy ECS services with rolling deployment or blue/green.
7. Run smoke tests:
   - `/health`
   - `/api/workflows/catalog`
   - one workflow run against a safe fixture
   - `/agent` startup
   - MCP tool list checks

Rollback:

- Frontend: point CloudFront/S3 deployment metadata back to previous asset version.
- ECS: redeploy previous ECR image tag.
- Neo4j: never auto-rollback data. Use explicit restore runbook.

## Fast Agent Deploys

Agent code must be independently deployable from API code.

Requirements:

- Separate Docker image or at least separate ECS service release.
- Agent prompts/config loaded from versioned files or controlled config.
- MCP tool contract tests before deploy.
- Fast smoke test that starts an agent session and lists tools.
- Ability to roll back only the agent service.

This allows prompt/tool/runtime fixes without redeploying the full product.

## Security

Public surface:

- CloudFront
- WAF
- ALB HTTPS for API/agent routes only

Private surface:

- ECS services
- MCP services
- Neo4j
- S3 buckets
- Secrets Manager

Minimum controls:

- HTTPS only.
- WAF rate limiting.
- auth lockout/backoff.
- least-privilege IAM per ECS task.
- private subnets for runtime services.
- no public Neo4j.
- no secrets in logs.

## Recommended Phase-1 Deployment

Build this first:

```text
CloudFront + S3 frontend
ALB
ECS service: API
ECS service: Agent
MCP as agent sidecars or private ECS services
Existing Neo4j EC2
S3 documents/backups
Secrets Manager
CloudWatch logs/alarms
CDK Python
```

Do not start with one monolithic Fargate service. It is acceptable for local development, but it is weak for production operations, agent scaling, deploy speed, and failure isolation.
