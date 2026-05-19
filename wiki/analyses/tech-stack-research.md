---
type: analysis
question: "What is the complete production technology stack for the Lead Intelligence Engine microservices system?"
date: 2026-04-26
tags: [tech-stack, tools, microservices, architecture, aws, python, temporal, database, websocket, llm]
sources_consulted:
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/service-scaling-strategy]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/execution-type-classification]]"
status: COMPLETE — 3 tool selections deferred to development phase; requirements locked below
---

# Technology Stack Research — Lead Intelligence Engine

**Question:** What is the complete production technology stack for the Lead Intelligence Engine microservices system?
**Date:** 2026-04-26
**Context:** AWS account confirmed. EC2 available. Microservices architecture (senior dev decision). ~300 leads/day MVP, 3 tenants. Team constraint: strong but not complex.

---

## Locked Decisions (No Further Discussion Needed)

These were decided during research and have no meaningful competing alternative.

| Layer | Decision | Reason |
|---|---|---|
| **Backend Language** | Python 3.12 | LLM ecosystem is Python-first. Anthropic SDK, LiteLLM, Temporal SDK all best-in-class on Python. Laravel/PHP is architecturally incompatible with this system — no LLM SDK, no workflow engine, no mature async patterns for agents. |
| **Backend Framework** | FastAPI + Uvicorn | Native async, Pydantic v2 for LLM output validation (critical for ScoringOutput schema), OpenAPI docs auto-generated. Reference architecture for LLM APIs in 2025. |
| **Package Manager** | uv | 10–100x faster than pip/poetry. New standard in Python 2025. |
| **LLM Provider — Primary** | Anthropic Claude Sonnet 4.6 | Prompt caching at 0.1x cost (90% discount on cached tokens) — cheaper than OpenAI's 0.175x. Reliable structured JSON via tool_use. Strong reasoning for lead scoring. |
| **LLM Provider — Fallback** | OpenAI GPT-4o | Via LiteLLM fallback chain. Only fires if Claude is unavailable. |
| **LLM SDK Abstraction** | LiteLLM | Unified API across providers (swap provider = change one env var). Built-in fallback routing, per-tenant cost tracking, virtual keys. Prevents vendor lock-in. |
| **Container Orchestration** | AWS ECS Fargate | Zero cluster ops. Per-service independent scaling. Predictable costs (~$107/month for 3 services). Scales from 300 leads/day to 100K+ without re-architecture. EKS is overkill for 3 services; Lambda has 15-min timeout that blocks orchestration. |
| **Secrets Management** | AWS Secrets Manager | AWS-native, IAM-integrated, ECS Fargate reads secrets at task startup. $0.40/secret/month. HashiCorp Vault is overkill for static API keys. |
| **Authentication / JWT** | Clerk | Native Organizations API = multi-tenancy out of the box. 4 RBAC roles (admin, team_lead, salesperson, viewer) are first-class. JWT includes `orgId` (maps to tenant_id) and `orgRole`. Free tier through 10K MAU. No Lambda triggers needed (unlike Cognito). |
| **Observability — Phase 1** | AWS CloudWatch | Native to AWS. ECS/RDS logs auto-collected. ~$5/month. Sufficient for MVP. |
| **Observability — Phase 2** | Grafana Cloud + Prometheus | Migrate Month 3+. Beautiful dashboards for quality_snapshots and LLM cost tracking. ~$39/month. Open standards, no vendor lock-in. |

---

## Three Tool Selections — Requirements Locked, Choice Deferred to Development

These three categories have two strong options each. The right answer depends on the team's operational capacity and budget preference. Both options in each pair are production-ready.

**Approach:** The mandatory requirements for each category are locked below. The team will evaluate candidate tools against these requirements during the development phase and record the final selection in the **Locked Decisions** section above. The research tables remain as reference material.

---

### Open Decision 1 — Workflow Orchestration Engine

**What this is:** The engine that runs Pipeline 1 and Pipeline 2. Manages sequential stages, parallel lead processing, crash recovery, and retry logic.

**Why this decision matters more than any other:** The architecture requires: *"If the orchestrator crashes mid-LLM-call, resume from the last completed pipeline_stage without re-running completed stages."* Most tools fail this test.

#### Full Landscape Researched

| Tool | Crash Recovery | Python SDK | MVP Cost | Ops Overhead | Notes |
|---|---|---|---|---|---|
| **Temporal (self-hosted on EC2)** | Native, deterministic | Excellent | ~$30/mo (t3.medium) | Medium | Best-in-class. Crash recovery is core product. |
| **Temporal Cloud** | Native, deterministic | Excellent | ~$75/mo | Very Low | Same as self-hosted, AWS manages server. |
| **AWS Step Functions** | State-level only — NOT mid-task | Moderate (JSON DSL) | ~$0.05/mo | Very Low | Cannot resume mid-LLM-call. Task restarts on crash. |
| **Netflix Conductor / Orkes (self-hosted)** | Native, deterministic | Good | ~$30/mo | Medium | Like Temporal but no determinism requirement. |
| **Orkes Cloud (Conductor)** | Native | Good | ~$3/mo at MVP | Very Low | Managed Conductor. Less known than Temporal. |
| **Hatchet (cloud)** | Good | Excellent | Free tier | Low | New (2024-2025). Less battle-tested. |
| **Inngest (cloud)** | Good (event replay) | Excellent | Free tier | Very Low | Event-driven model. New but promising. |
| **Prefect (self-hosted)** | Task-level | Excellent | ~$30/mo | Medium | Built for data pipelines, not orchestration. |
| **Celery + Canvas** | No native crash recovery | Excellent | ~$15/mo (Redis) | Medium | Job queue, not workflow engine. Needs custom recovery code. |
| **Apache Airflow / MWAA** | Task-level | Excellent | $320+/mo | High | Overkill. Built for data teams with large DAGs. |
| **Restate.dev** | Native | Good | Free tier | Low | Very early stage. Not production-recommended yet. |
| **DIY state machine (FastAPI + Postgres)** | Manual build | N/A | $0 | High (you build it) | Viable for 2-3 stages, not 6 stages + LLM + parallel. |

**Disqualified immediately:** Celery (no native recovery), Airflow/MWAA (overkill, data team tool), Restate (too early), DIY (too complex for this pipeline).

#### The Two Real Options

**Option A — Temporal self-hosted on EC2**

- Run Temporal server as a Docker container on a dedicated t3.medium EC2 instance
- Cost: ~$30/month
- Every Pipeline stage = a Temporal Activity. Every Pipeline run = a Temporal Workflow
- If orchestrator crashes mid-Scoring-Agent-call: Temporal replays from the last completed Activity boundary. The LLM call may be retried once (accepted trade-off, already documented in orchestration-layer-spec Section 8.4)
- "Beehive" alignment: adding a new agent = register a new Workflow. Zero changes to existing code
- Requires: team comfortable managing one Docker container on EC2

**Option B — AWS Step Functions**

- Fully managed, zero server management
- Cost: ~$0.05/month at MVP volume
- Pipeline stages = Step Functions states defined in JSON (Amazon States Language)
- Crash recovery limitation: if a Lambda crashes mid-task, that task restarts from the beginning (not mid-LLM-call resumption). This means a potential double LLM call on crash — same trade-off as Temporal but less configurable
- "Beehive" alignment: adding a new agent = define a new state machine. Works, but JSON DSL is verbose
- Requires: team comfortable with Amazon States Language DSL

| | Temporal (self-hosted) | Step Functions |
|---|---|---|
| Mid-task crash recovery | Yes, native | No — task restarts |
| Python workflow code | Yes, Pythonic decorators | No — JSON DSL |
| Cost | ~$30/month | ~$0.05/month |
| Ops burden | Medium (one Docker container) | Zero |
| "Beehive" extensibility | Excellent | Good |
| Battle-tested | Yes (Uber, Stripe, Robinhood) | Yes (AWS native) |

**Recommendation from research:** Temporal self-hosted. The mid-task crash recovery and Pythonic workflow code are worth $30/month and the ops overhead of one Docker container. If the team has zero ops capacity: Step Functions.

**Tool selection deferred to development.** The team will finalize this choice when the pipeline stage is being implemented. Any tool selected MUST satisfy all of the following requirements:

#### Workflow Orchestration — Mandatory Requirements

| # | Requirement | Why it is non-negotiable |
|---|---|---|
| R1 | **Per-stage crash recovery** — if the orchestrator crashes mid-execution, the system must be able to resume from the last successfully completed pipeline stage, not restart from the beginning | Prevents duplicate LLM calls and data corruption on crash |
| R2 | **Native Python SDK** — workflow and activity definitions must be written in Python, not a DSL (JSON, YAML, XML) | The entire backend is Python; a DSL adds a translation layer with no benefit |
| R3 | **Async-safe execution** — must support concurrent execution of multiple leads per tenant without shared state | Pipeline 1 processes up to N leads in parallel |
| R4 | **Retry logic per step** — must support configurable retry counts and backoff per activity type, not just per workflow | Different stages (LLM call vs enrichment API) need different retry policies |
| R5 | **Timeout enforcement per step** — must support per-activity timeouts | Scoring Agent calls have a 30-second timeout; enrichment calls have a different limit |
| R6 | **Workflow state visibility** — must expose a query/inspection interface to see which pipeline stage a given lead is currently at | Required for the DevOps dashboard and crash recovery path |
| R7 | **Durable state persistence** — workflow state must survive the orchestrator process restarting | The crash safety guarantee in orchestration-layer-spec §8.1 depends on this |

---

### Open Decision 2 — Real-time WebSocket / Chat Delivery

**What this is:** The infrastructure that pushes lead cards to salespeople in real-time in the web chat interface. Also handles HOT lead push notifications.

#### Full Landscape Researched

| Platform | Self-Hostable | Pusher-Compatible | Push Notifications | 100 Concurrent | 500 Concurrent | Ops Burden |
|---|---|---|---|---|---|---|
| **Pusher Channels + Beams** | No | Native | Yes (Beams) | $49/mo | $299/mo | None |
| **Ably** | No | No | Yes (built-in) | $30/mo | $150/mo | None |
| **Soketi (EC2 self-hosted)** | Yes | Yes (drop-in) | No (need FCM) | ~$35/mo | ~$35/mo | Low |
| **Centrifugo (EC2 self-hosted)** | Yes | No | No (need FCM) | ~$35/mo | ~$35/mo | Low-Medium |
| **Socket.io (EC2 self-hosted)** | Yes | No | No (need FCM) | ~$35/mo | ~$35/mo | Medium |
| **AWS API Gateway WebSocket** | No (AWS-managed) | No | Requires SNS setup | $20-50/mo | $200-300/mo | Low (but expensive at scale) |
| **Firebase Realtime DB** | No | No | Via FCM (free) | $5-40/mo | $20-80/mo | Low |
| **PubNub** | No | No | Yes (built-in) | $49/mo | $249/mo | None |
| **Supabase Realtime** | No | No | Via external | $25/mo flat | $25/mo flat | None |
| **StreamChat SDK** | No | No | Yes | $99/mo | $99/mo | None (full chat features) |
| **AppSync (GraphQL subscriptions)** | No | No | External | $0-40/mo | $0-40/mo | Low (if GraphQL) |

**Disqualified:** AWS API Gateway WebSocket gets expensive at scale ($200-300/month at 500 concurrent vs $35-50/month self-hosted). AppSync only makes sense if the API is GraphQL. StreamChat is a full chat product — overkill for lead card delivery. Liveblocks is collaboration, not pub/sub.

**On Soketi specifically — production-ready?** Yes. Actively maintained. API-compatible with Pusher (same Pusher SDK on both client and backend). Key advantage: start self-hosted with Soketi, migrate to managed Pusher later by changing three environment variables. Zero code changes.

**Push notifications on self-hosted options:** Need a separate service. **Firebase FCM** is the answer — free, handles web push + mobile push, integrates with any backend via HTTP API.

#### The Two Real Options

**Option A — Pusher Channels + Pusher Beams**

- Fully managed, zero infrastructure
- Cost: $49/month (100 concurrent) to $299/month (500 concurrent)
- Push notifications included via Pusher Beams (+$10/month)
- Per-user rooms native (channel per `user_id`)
- Python SDK: `pusher-http-python` — dead simple

```python
pusher_client.trigger(f'private-user-{user_id}', 'lead-card', {
    'lead_id': lead.id,
    'score': lead.score,
    'bucket': lead.bucket,
    'reasoning': lead.reasoning
})
```

**Option B — Soketi (self-hosted on EC2) + Firebase FCM**

- Soketi runs as a Docker container on EC2 (~$35/month)
- Soketi is Pusher-compatible — exact same Python client code as Option A
- Firebase FCM handles push notifications (free)
- Cost: ~$35-50/month regardless of concurrent user count
- If you outgrow Soketi or want to remove ops overhead: change 3 env vars → now running on Pusher. Zero code changes

| | Pusher + Beams | Soketi + FCM |
|---|---|---|
| Push notifications | Yes (Beams, $10/mo extra) | Yes (FCM, free) |
| 100 concurrent | $49/mo | ~$35/mo |
| 500 concurrent | $299/mo | ~$35/mo (same) |
| Ops burden | None | Low (one Docker container) |
| Migration path | N/A (already managed) | To Pusher = change 3 env vars |
| Code changes between options | None — same Pusher SDK | None — Pusher-compatible |

**Recommendation from research:** Soketi on EC2 at MVP. Same code as Pusher. Saves $14-264/month. Migrate to Pusher later if team wants to eliminate the EC2 container.

**Tool selection deferred to development.** The team will finalize this choice when the Delivery and Integration Layer is being implemented. Any tool selected MUST satisfy all of the following requirements:

#### Real-time WebSocket / Chat Delivery — Mandatory Requirements

| # | Requirement | Why it is non-negotiable |
|---|---|---|
| R1 | **Private per-user channels** — each salesperson must receive only their own lead cards; cross-tenant or cross-user leakage is a hard security violation | Multi-tenant isolation requirement |
| R2 | **Python server-side SDK** — the Orchestration Service must be able to push events to a channel from Python without a separate relay service | All backend services are Python |
| R3 | **Web push notifications** — must support HOT lead push notifications to salesperson browsers even when the tab is not in focus | HOT leads require notification within the SLA window |
| R4 | **Supports at least 100 simultaneous connections at MVP** — 3 tenants × ~30 salespeople = ~90 concurrent at peak | MVP scale baseline |
| R5 | **Message delivery guarantee** — events pushed while a client is disconnected must be deliverable on reconnect (missed event replay or client-side polling fallback) | Salesperson must not miss a HOT lead due to a brief disconnection |
| R6 | **Environment-level isolation** — dev, staging, and prod channels must be strictly isolated; a staging event must never reach a production client | Prevents test data from appearing in production dashboards |

---

### Open Decision 3 — PostgreSQL Hosting

**What this is:** Where the PostgreSQL database runs. Row-Level Security (RLS) is required for multi-tenant isolation — all options below support it natively.

#### Full Landscape Researched

| Service | MVP Cost | HA/Failover RTO | Ops Burden | AWS-Native | Backups |
|---|---|---|---|---|---|
| **Aurora Serverless v2** | ~$94/mo | ~30 seconds (automatic) | Very Low | Yes | Auto, 35-day retention |
| **Aurora Provisioned (t4g.medium)** | ~$136/mo | ~30 seconds (automatic) | Very Low | Yes | Auto, 35-day retention |
| **RDS PostgreSQL (t3.medium)** | ~$129/mo | Manual or Multi-AZ (+$79) | Very Low | Yes | Auto, 35-day retention |
| **PostgreSQL self-hosted on EC2 (t3.medium)** | ~$42/mo | 5-30 minutes (manual restore) | Medium-High | Yes (your account) | Manual to S3 |
| **Neon** | ~$19/mo | Automatic | Very Low | No (external) | Auto |
| **Supabase** | ~$25/mo | Automatic | Very Low | No (external) | Auto |
| **CockroachDB Cloud** | ~$400+/mo | Automatic, distributed | Medium | No | Auto |
| **TimescaleDB** | ~$50+/mo | Varies | Medium | No | Auto |
| **Railway PostgreSQL** | ~$30/mo | Automatic | Very Low | No | Auto |

**Disqualified:** CockroachDB (distributed SQL overkill for MVP). TimescaleDB (time-series extension not needed for lead data). Neon/Supabase/Railway are good products but not AWS-native — data lives outside your AWS account.

**On PostgreSQL self-hosted on EC2 — honest assessment:**

At 300 leads/day with 50GB data, it technically works. The honest risks:

- If the EC2 instance fails, RTO = 5–30 minutes to restore from S3 snapshot (vs Aurora's ~30 seconds)
- Your team owns: OS security patching, disk space monitoring, VACUUM scheduling, backup automation and testing, read replica setup
- The saving is ~$52/month vs Aurora Serverless v2
- If the team has run production PostgreSQL before and is comfortable: viable
- If this is a first production database: use Aurora

#### The Two Real Options

**Option A — Aurora PostgreSQL Serverless v2**

- Auto-scales from 0.5 ACU to 128 ACU based on load
- At 300 leads/day (bursty): scales down to 0.5 ACU nights/weekends → cost-optimal
- Cost: ~$94/month at MVP
- Zero ops: AWS manages patching, backups, failover, scaling
- Read replica for Reporting Service: one config change

**Option B — PostgreSQL self-hosted on EC2 (t3.medium)**

- Standard PostgreSQL on a t3.medium instance ($32/month EC2 + $10/month EBS)
- Cost: ~$42/month
- Team owns: backups (pg_dump → S3 cron), monitoring, patching, failover
- RLS works identically to Aurora — no code difference
- If EC2 fails: restore from latest S3 snapshot. Time depends on snapshot recency and data size

| | Aurora Serverless v2 | PostgreSQL on EC2 |
|---|---|---|
| Cost | ~$94/mo | ~$42/mo |
| RTO on failure | ~30 seconds | 5-30 minutes |
| Ops burden | None | Medium-High |
| Read replicas | One config change | Manual WAL replication setup |
| Backups | Automatic, 35-day retention | Manual cron job to S3 |
| RLS support | Native PostgreSQL | Native PostgreSQL |
| Auto-scaling | Yes (Serverless v2) | No |

**Recommendation:** Aurora Serverless v2. The $52/month saving from self-hosting is not worth the operational risk unless the team has a dedicated database operator.

**Hybrid option for cost-sensitive early stage:** Run RDS t3.micro (~$27/month) for the first 30 days while validating the product, then migrate to Aurora Serverless v2. Schema is identical — migration is a pg_dump/pg_restore. This costs ~$27 in month 1 instead of $94.

**Tool selection deferred to development.** The team will finalize this choice when the data layer is being provisioned. Any hosting option selected MUST satisfy all of the following requirements:

#### PostgreSQL Hosting — Mandatory Requirements

| # | Requirement | Why it is non-negotiable |
|---|---|---|
| R1 | **PostgreSQL 15+ compatibility** — the system uses Row-Level Security (RLS), generated columns, and JSONB with GIN indexing | Schema and query layer depend on these features |
| R2 | **Row-Level Security (RLS) enforced at the database level** — every table with tenant data must enforce `tenant_id` isolation via RLS policies, not just application-layer filtering | Multi-tenant isolation is a security requirement, not a convenience |
| R3 | **Automated backups with point-in-time recovery** — must support restoring to any point within at least 7 days | Lead scoring data and lineage records are business-critical |
| R4 | **Connection pooling support** — must work with PgBouncer or an equivalent pooler; ECS Fargate services cannot maintain persistent connections at scale | ECS tasks are ephemeral; without pooling, each task restart opens a new connection |
| R5 | **Secrets-manager-compatible credential rotation** — database credentials must be storable in and rotatable via the secrets vault (AWS Secrets Manager) without application downtime | Matches the security policy in [[analyses/security-planning]] |
| R6 | **Minimum 99.5% monthly availability SLA** | Production workload with paying tenants |
| R7 | **Read-replica support** — the Reporting Service must be able to query a read replica to avoid load on the primary | Quality metrics queries (weekly SQL jobs) must not affect pipeline throughput |

---

## Complete Stack — Two Budget Scenarios

### Scenario A — Managed (Lowest Ops Overhead)

| Layer | Tool | Cost/Month |
|---|---|---|
| Language + Framework | Python 3.12 + FastAPI + Uvicorn | $0 |
| Package Manager | uv | $0 |
| Workflow Orchestration | Temporal Cloud | ~$75 |
| Job Queue / Ingestion Buffer | Redis (AWS ElastiCache t3.micro) + Celery | ~$15 |
| LLM Primary | Anthropic Claude Sonnet 4.6 via LiteLLM | ~$3/day (cached) |
| LLM Fallback | OpenAI GPT-4o via LiteLLM | fallback only |
| Database | Aurora PostgreSQL Serverless v2 | ~$94 |
| Real-time Chat | Pusher Channels | ~$49 |
| Push Notifications | Pusher Beams | ~$10 |
| Containers | AWS ECS Fargate (3 services) | ~$107 |
| Auth + Multi-tenancy | Clerk | $0 (free tier) |
| Secrets | AWS Secrets Manager | ~$2.50 |
| Observability | AWS CloudWatch | ~$5 |
| **Total (excl. LLM tokens)** | | **~$357/mo** |

### Scenario B — Hybrid Self-Hosted (Lower Cost, More Ops)

| Layer | Tool | Cost/Month |
|---|---|---|
| Language + Framework | Python 3.12 + FastAPI + Uvicorn | $0 |
| Package Manager | uv | $0 |
| Workflow Orchestration | Temporal self-hosted on EC2 (t3.medium) | ~$30 |
| Job Queue / Ingestion Buffer | Redis (AWS ElastiCache t3.micro) + Celery | ~$15 |
| LLM Primary | Anthropic Claude Sonnet 4.6 via LiteLLM | ~$3/day (cached) |
| LLM Fallback | OpenAI GPT-4o via LiteLLM | fallback only |
| Database | Aurora PostgreSQL Serverless v2 | ~$94 |
| Real-time Chat | Soketi on EC2 (t3.small) | ~$35 |
| Push Notifications | Firebase FCM | $0 |
| Containers | AWS ECS Fargate (3 services) | ~$107 |
| Auth + Multi-tenancy | Clerk | $0 (free tier) |
| Secrets | AWS Secrets Manager | ~$2.50 |
| Observability | AWS CloudWatch | ~$5 |
| **Total (excl. LLM tokens)** | | **~$288/mo** |

---

## LLM Cost Estimate

At 300 leads/day, 1 LLM call per lead (Scoring Agent only):

| | First run of day | Subsequent runs (cached system message) |
|---|---|---|
| Input tokens per lead | ~2,000 (system) + ~300 (lead data) | ~300 (uncached) + ~2,000 at 0.1x |
| Output tokens per lead | ~200 | ~200 |
| Cost per lead (Claude Sonnet 4.6) | ~$0.006 | ~$0.003 |
| Cost per day (300 leads) | ~$1.80 first lead, ~$0.90 rest | ~$0.90/day steady state |
| Cost per month | | **~$27/month** |

Plus 3 Pipeline 2 LLM calls per tenant onboarding (one-time, ~$0.05 total per tenant).

---

## Open Items — What This Document Does Not Cover

The following were flagged as TBD in the source architecture documents and are not blocked by tech stack choices, but need team decisions:

1. **Signal `detection_rule` format** — **RESOLVED 2026-04-28.** Named extractor + params model. See [[analyses/signal-detection-rule-spec]].
2. **Per-tenant Scoring Agent concurrency cap** — recommend 2 per tenant. Needs team decision based on provider rate limits.
3. **`needs_review` threshold** — 0.6 or 0.75. Team decision after Month 1 baseline.
4. **WARM SLA window** — **RESOLVED: 48 hours (locked — planning audit FIX-011, 2026-05-20).** AR1 metric is now calculable.
5. **Pipeline 2 check-in cadence** — 2-week or monthly.
6. **Alert delivery channel** — chat only, or chat + email for critical failures.
7. **Dashboard tooling** — in-product React tab vs Grafana vs Metabase. Grafana Cloud connects directly to `quality_snapshots` via read-only DB connection.
8. **CRM integrations** — which CRMs to support at MVP. HubSpot has the best Python SDK and free tier for testing; Salesforce for enterprise.

---

## What Was Ruled Out and Why

| Tool | Category | Why Ruled Out |
|---|---|---|
| Laravel / PHP | Backend | No LLM SDK, no async-first framework, no agent ecosystem. Architecturally incompatible. |
| Go + Gin | Backend | Best raw throughput irrelevant when bottleneck is LLM latency. SDK ecosystem fights you. |
| Node.js | Backend | Viable but second choice. LLM ecosystem is Python-first. |
| Celery (as orchestrator) | Orchestration | Job queue, not workflow engine. No native crash recovery. Requires custom recovery code = reinventing Temporal. |
| Airflow / MWAA | Orchestration | Built for large data teams, not microservice orchestration. $320+/month for MWAA. |
| Prefect / Dagster | Orchestration | Data pipeline tools. Asset-centric model doesn't fit lead orchestration. |
| AWS EKS | Containers | Kubernetes expertise required. Overkill for 3-5 services. For 50+ microservices. |
| AWS Lambda | Containers | 15-minute execution timeout blocks orchestration. Cold starts hurt real-time chat. |
| AWS API Gateway WebSocket | Real-time | Gets expensive at 500+ concurrent ($200-300/month vs $35-49/month alternatives). Manual connection tracking code. |
| Socket.io | Real-time | More complex than Soketi/Centrifugo. Adds Node.js runtime to manage. |
| Neon / Supabase | Database | Not AWS-native. Data lives outside your AWS account. Compliance risk at scale. |
| CockroachDB | Database | Distributed SQL overkill for MVP. $400+/month. |
| HashiCorp Vault | Secrets | Dynamic secrets not needed for static API keys. Overkill. |
| Auth0 | Auth | $600+/month minimum. Not viable for MVP. |
| Datadog | Observability | ~$380/month at MVP. Premium features not needed yet. Start with CloudWatch. |
| Groq | LLM | No prompt caching support. Critical for cost control at this system's architecture. |

---

## Follow-up — During Development

When each tool category is being implemented, evaluate candidates against the locked requirements above and record the final selection in the **Locked Decisions** table at the top of this document. Capture:

- **Selected tool** — name and version
- **Why it was chosen** — which requirements it meets and any trade-offs accepted
- **Configuration decisions** — hosting model (self-hosted vs managed), region, instance size
- **Date locked**

Remaining open items (non-blocking):

1. ~~Lock signal `detection_rule` format~~ — **RESOLVED 2026-04-28.** See [[analyses/signal-detection-rule-spec]].
2. Confirm: HubSpot as first CRM integration target? (best Python SDK, free dev tier)
3. Per-tenant Scoring Agent concurrency cap — recommend 2; confirm against provider rate limits during development.
4. `needs_review` threshold — 0.6 or 0.75; team decision after Month 1 baseline.
5. Pipeline 2 check-in cadence — 2-week or monthly.
6. Alert delivery channel — chat only, or chat + email for critical failures.
7. Dashboard tooling — in-product React tab vs Grafana vs Metabase.
