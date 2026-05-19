---
type: analysis
question: "What services, environment variables, and capabilities does a developer need to run the Lead Intelligence Engine locally?"
date: 2026-05-20
tags: [dev-environment, setup, services, environment-variables, local-development, infrastructure]
sources_consulted:
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/security-planning]]"
  - "[[analyses/inngest-function-design]]"
  - "[[analyses/lead-enrichment-architecture]]"
  - "[[analyses/meta-integration-implementation]]"
  - "[[analyses/orchestration-layer-spec]]"
status: COMPLETE
---

# Dev Environment Requirements — Lead Intelligence Engine

**Question:** What services, environment variables, and capabilities does a developer need to run the Lead Intelligence Engine locally?
**Date:** 2026-05-20

---

## Plain-English Summary

**Why this exists:** This document defines *what* the dev environment needs, not *how* to set it up. The tech stack is partially locked and partially deferred (to be finalized in Sprint 1). A developer reading this knows exactly which services to provision, which credentials to request, and what the environment must be capable of before they can run a lead end-to-end.

**What is locked vs deferred:**

| Component | Status | Decision |
|---|---|---|
| Language + framework | Locked | Python 3.12 + FastAPI + Uvicorn |
| Package manager | Locked | `uv` |
| LLM provider | Locked | Anthropic Claude Sonnet 4.6 (primary), OpenAI GPT-4o (fallback via LiteLLM) |
| LLM proxy | Locked | LiteLLM |
| Auth + multi-tenancy | Locked | Clerk (Organizations API) |
| Secrets management | Locked | AWS Secrets Manager |
| Observability | Locked | AWS CloudWatch (Phase 1) |
| Deployment target | Locked | AWS ECS Fargate |
| Workflow orchestration | Decision pending Sprint 1 | Inngest (strong candidate; Python SDK confirmed available) vs Temporal |
| PostgreSQL hosting | Decision pending Sprint 1 | AWS Aurora Postgres vs self-managed on EC2 |
| Real-time delivery | Decision pending Sprint 1 | Pusher vs Soketi |

**Deferred decisions do not block local development.** Postgres runs locally via Docker. Inngest runs locally via its dev server. Real-time delivery is not required for Pipeline 1 correctness testing.

---

## Section 1 — Services Required

Every service listed here must be available (locally or reachable) before the system can process a lead end-to-end.

### 1.1 Core Services (must run locally)

| Service | What it does | Local approach |
|---|---|---|
| **PostgreSQL (compatible)** | 32-entity data model, RLS-based tenant isolation, all pipeline state | Docker container (`postgres:16-alpine`) |
| **Workflow orchestration** | Runs Pipeline 1, Pipeline 2, scheduled jobs | Inngest Dev Server (local; zero config) or Temporal Dev Server |
| **LiteLLM proxy** | Routes LLM calls to Anthropic (primary) and OpenAI (fallback); centralises model config | Docker container or `litellm` process |

### 1.2 External Services (cloud; developer needs credentials)

| Service | What it does | Notes |
|---|---|---|
| **Anthropic API** | Claude Sonnet 4.6 — Message Parser and Rating Agent | Requires `ANTHROPIC_API_KEY`. Paid per token. |
| **OpenAI API** | GPT-4o — LiteLLM fallback path | Requires `OPENAI_API_KEY`. Only used when Anthropic call fails. |
| **Clerk** | JWT issuance, multi-tenancy, RBAC | Requires Clerk account with a development app configured. Free ≤10K MAU. |
| **AWS Secrets Manager** | Credential vault for PII encryption key, enrichment API keys, Postgres connection string | Requires AWS IAM role with Secrets Manager read access. |
| **AWS CloudWatch** | Application logs, metrics, alerts | Requires AWS credentials with CloudWatch Logs write access. |

### 1.3 Enrichment APIs (can mock locally; real credentials for integration tests)

The system calls 9 enrichment providers. In local development, mock responses from the fixture library (see [[analyses/test-strategy]] §Test Data) cover the standard paths. Real credentials are needed only for integration tests or full E2E runs.

| Provider | What it enriches | Mock available |
|---|---|---|
| Truecaller | Phone number → name, carrier | ✓ |
| Apollo.io | Email/LinkedIn → company profile, funding | ✓ |
| Surepass | GSTIN / Aadhaar verification (India) | ✓ |
| Probe42 | Indian MCA company registry | ✓ |
| Tracxn | Startup data, funding rounds | ✓ |
| NewsCatcherAPI | News mentions for company/person | ✓ |
| IndiaMART / JustDial | SMB business listings | ✓ |
| Serper.dev | Google Search results | ✓ |
| Google Places | Location verification, business type | ✓ |

### 1.4 Channel Connectors (external; require tunnel for local receipt)

| Channel | Used for | Local requirement |
|---|---|---|
| Meta (WhatsApp, Facebook, Instagram) | Inbound DMs and Lead Ads | ngrok or equivalent tunnel to receive webhooks; `META_VERIFY_TOKEN` for initial handshake |
| Email | Inbound email lead parsing | Email webhook provider (e.g. Postmark, SendGrid inbound) + tunnel |
| Google Sheets | CSV-style lead import | OAuth credentials for Sheets API; no tunnel needed |

**Note:** Webhook receipt is only needed when testing the inbound channel path end-to-end. For Pipeline 1 and Pipeline 2 testing, leads can be injected directly via `POST /v1/leads` or the test fixture loader.

---

## Section 2 — Environment Variables

All environment variables are loaded from a `.env` file (local development only). In production, every secret is fetched from AWS Secrets Manager — no secret values appear in ECS task definitions or source control.

**Rule:** The `.env` file must never be committed. Add `.env` to `.gitignore` on repo creation. Provide a `.env.example` with all variable names but no values.

### 2.1 LLM

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key — Sonnet 4.6 calls (Message Parser + Rating Agent) |
| `OPENAI_API_KEY` | Yes | OpenAI fallback key — used by LiteLLM when Anthropic call fails |
| `LITELLM_BASE_URL` | Yes | URL of local or hosted LiteLLM proxy (e.g. `http://localhost:4000`) |
| `LITELLM_MASTER_KEY` | Yes | LiteLLM internal auth key — set during LiteLLM proxy setup |
| `DEFAULT_SCORING_MODEL` | No | Default: `claude-sonnet-4-6` — override in dev to use cheaper model |
| `DEFAULT_PARSER_MODEL` | No | Default: `claude-haiku-4-5` — Message Parser model |

### 2.2 Authentication (Clerk)

| Variable | Required | Description |
|---|---|---|
| `CLERK_SECRET_KEY` | Yes | Server-side Clerk secret — used by FastAPI middleware to verify JWTs |
| `CLERK_PUBLISHABLE_KEY` | Yes | Client-side key — used by frontend Clerk SDK |
| `CLERK_WEBHOOK_SECRET` | Yes | Clerk webhook signing secret — for login event → access_log writes |
| `CLERK_JWKS_URL` | No | Auto-resolved from `CLERK_SECRET_KEY`; override only if testing against a different Clerk instance |

### 2.3 Database

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres connection string — `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `DATABASE_POOL_SIZE` | No | Default: `10` — max connections per service instance |
| `DATABASE_SSL_MODE` | No | Default: `require` (production) / `disable` (local Docker) — set to `disable` for local Postgres |

### 2.4 Encryption

| Variable | Required | Description |
|---|---|---|
| `PII_ENCRYPTION_KEY` | Yes | 32-byte AES-256 key for PII field encryption — base64-encoded. In production this is fetched from Secrets Manager path `global/db/pii_encryption_key`. For local dev, generate with `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"` |

### 2.5 Workflow Orchestration

**If using Inngest (current strong candidate):**

| Variable | Required | Description |
|---|---|---|
| `INNGEST_EVENT_KEY` | Yes | Inngest event signing key — identifies the app when sending events |
| `INNGEST_SIGNING_KEY` | Yes | Inngest function signing key — validates incoming Inngest calls to the API |
| `INNGEST_DEV_SERVER_URL` | No | Default: `http://localhost:8288` — override if running Inngest Dev Server on a different port |

**If using Temporal:**

| Variable | Required | Description |
|---|---|---|
| `TEMPORAL_HOST` | Yes | Temporal server address — `localhost:7233` for local |
| `TEMPORAL_NAMESPACE` | No | Default: `lead-engine-dev` |
| `TEMPORAL_TASK_QUEUE` | No | Default: `lead-processing` |

### 2.6 Meta / Channel Connectors

| Variable | Required | Description |
|---|---|---|
| `META_APP_ID` | Yes (channel path) | Meta App ID — identifies the app to Meta platform |
| `META_APP_SECRET` | Yes (channel path) | Used for HMAC-SHA256 validation of incoming Meta webhooks |
| `META_VERIFY_TOKEN` | Yes (channel path) | Token returned during Meta webhook subscription verification handshake |
| `WEBHOOK_TUNNEL_URL` | No | Public URL of ngrok / Cloudflare tunnel — required for Meta webhook configuration in dev |

### 2.7 Enrichment API Keys

One variable per provider. All are optional for local development (mock responses cover standard paths). Required for integration tests and E2E runs.

| Variable | Provider |
|---|---|
| `TRUECALLER_API_KEY` | Truecaller |
| `APOLLO_API_KEY` | Apollo.io |
| `SUREPASS_API_KEY` | Surepass |
| `PROBE42_API_KEY` | Probe42 |
| `TRACXN_ACCESS_TOKEN` | Tracxn |
| `NEWSCATCHER_API_TOKEN` | NewsCatcherAPI |
| `SERPER_API_KEY` | Serper.dev |
| `GOOGLE_PLACES_API_KEY` | Google Places |
| `INDIAMART_API_KEY` | IndiaMART |

### 2.8 AWS

| Variable | Required | Description |
|---|---|---|
| `AWS_REGION` | Yes | AWS region — e.g. `ap-south-1` (Mumbai, closest to primary user base) |
| `AWS_CLOUDWATCH_LOG_GROUP` | Yes | CloudWatch log group name — e.g. `/lead-engine/dev` |
| `AWS_ACCESS_KEY_ID` | Yes (local) | AWS credential — IAM user or role with CloudWatch + Secrets Manager access |
| `AWS_SECRET_ACCESS_KEY` | Yes (local) | Companion to above |
| `SECRETS_MANAGER_ENABLED` | No | Default: `true` in production. Set to `false` in local dev to read secrets from `.env` directly (bypasses Secrets Manager fetch) |

### 2.9 Application

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | Yes | `development` / `staging` / `production` — controls log level, SSL enforcement, mock behaviour |
| `LOG_LEVEL` | No | Default: `INFO`. Set to `DEBUG` in local dev for full request/response tracing. |
| `API_PORT` | No | Default: `8000` — FastAPI/Uvicorn port |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated list — `http://localhost:3000` for local frontend dev |
| `RESCORE_COOLDOWN_HOURS` | No | Default: `24` — minimum hours between manual Pipeline 1 re-runs for the same lead |

### 2.10 Feature Flags

Feature flags gate optional enrichment providers and experimental paths. All default to `true` (enabled) in development unless overridden.

| Variable | Default | Controls |
|---|---|---|
| `FEATURE_ENRICHMENT_TRUECALLER` | `true` | Enable Truecaller phone enrichment step |
| `FEATURE_ENRICHMENT_APOLLO` | `true` | Enable Apollo company enrichment step |
| `FEATURE_ENRICHMENT_SUREPASS` | `true` | Enable Surepass GSTIN verification step |
| `FEATURE_ENRICHMENT_PROBE42` | `true` | Enable Probe42 MCA lookup step |
| `FEATURE_ENRICHMENT_TRACXN` | `true` | Enable Tracxn startup data step |
| `FEATURE_ENRICHMENT_NEWSCATCHER` | `true` | Enable NewsCatcherAPI news mentions step |
| `FEATURE_ENRICHMENT_GOOGLE_PLACES` | `true` | Enable Google Places location verification |
| `FEATURE_PRE_FILTER_GATE` | `true` | Enable DM path pre-filter (discards noise before LLM) |
| `FEATURE_SCORE_DECAY` | `true` | Enable scheduled score decay job |

---

## Section 3 — Capability Checklist

Before claiming a dev environment is ready, every item below must be verified.

| Capability | How to verify |
|---|---|
| Run database migrations | `uv run python manage.py migrate` completes without errors; 32 tables created |
| Apply Postgres RLS policies | Connect as a non-superuser and confirm cross-tenant data is not visible |
| Execute Pipeline 2 (onboarding) | POST to `/v1/onboarding/business-profile` with test tenant payload → orchestration job starts, all 5 LLM steps complete, `tenant.status` transitions to `active` |
| Execute Pipeline 1 (per-lead) | POST to `/v1/leads` with `fixture_hot_b2b.json` payload → lead reaches `scored` stage, bucket = `hot`, `lineage_record` rows created |
| Route LLM calls through LiteLLM | Trigger a scoring call, confirm request appears in LiteLLM logs with correct model ID |
| Verify Clerk JWT | Call a protected endpoint with a valid Clerk JWT → 200; with expired/malformed token → 401 |
| Validate HMAC on inbound webhook | POST to `/v1/webhooks/meta/whatsapp` with correct `X-Hub-Signature-256` → 200; tampered signature → 403 |
| Receive real Meta webhook | Configure ngrok URL in Meta developer console; send a test WhatsApp DM → webhook received, lead ingested |
| Read secret from Secrets Manager | Start the app with `SECRETS_MANAGER_ENABLED=true` → confirm `PII_ENCRYPTION_KEY` loaded from vault, not `.env` |
| Write logs to CloudWatch | Trigger any pipeline stage → confirm structured log lines appear in the configured log group |
| Run full test suite | `uv run pytest` completes; unit tests < 60 seconds; all green |
| Run E2E golden path | Golden Path 1 (HOT B2B) completes within 120 seconds; all assertions pass (see [[analyses/test-strategy]] §Layer 3) |

---

## Section 4 — Setup Instructions Template

**Status:** Skeleton only. To be completed in Sprint 1 once deferred tech stack decisions (Postgres hosting, orchestration tool, real-time delivery) are finalized.

### Prerequisites

- [ ] Python 3.12 installed
- [ ] `uv` installed (`pip install uv` or `brew install uv`)
- [ ] Docker Desktop running
- [ ] AWS CLI configured (`aws configure`) with dev IAM credentials
- [ ] Clerk account created; development app configured; API keys copied
- [ ] ngrok (or Cloudflare tunnel) installed — required for Meta webhook receipt
- [ ] `.env` created from `.env.example` and populated

### Database Setup

```bash
# Start local Postgres
docker run -d \
  --name lead-engine-db \
  -e POSTGRES_USER=dev \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=leadengine \
  -p 5432:5432 \
  postgres:16-alpine

# Run migrations
uv run python manage.py migrate

# Seed test tenant and fixtures
uv run python manage.py seed --env=development
```

### Orchestration Service Setup

**If Inngest:**

```bash
# Install Inngest CLI
npm install -g inngest-cli

# Start Inngest Dev Server (port 8288)
inngest dev

# Register functions (runs with FastAPI app — auto-discovered)
# No separate step needed — functions register on app startup
```

**If Temporal:**

```bash
# Start Temporal Dev Server
temporal server start-dev

# Worker starts alongside the FastAPI app
# See: src/workers/temporal_worker.py
```

### LiteLLM Proxy Setup

```bash
# Create LiteLLM config
cat > litellm_config.yaml << 'EOF'
model_list:
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: gpt-4o-fallback
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
EOF

# Start LiteLLM (port 4000)
litellm --config litellm_config.yaml --port 4000
```

### Running Locally

```bash
# Install dependencies
uv sync

# Start FastAPI dev server (hot reload)
uv run uvicorn app.main:app --reload --port 8000

# Verify: GET http://localhost:8000/health → {"status": "ok"}
```

### Testing a Lead End-to-End

```bash
# 1. Seed test tenant (if not already done)
uv run python manage.py seed --env=development

# 2. Submit a test lead using the HOT B2B fixture
curl -X POST http://localhost:8000/v1/leads \
  -H "Authorization: Bearer <clerk_jwt_for_test_tenant>" \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/fixture_hot_b2b.json

# 3. Watch the pipeline in the Inngest Dev Server UI: http://localhost:8288

# 4. Verify the lead card
curl http://localhost:8000/v1/leads/<lead_id>/card \
  -H "Authorization: Bearer <clerk_jwt>"
# Expect: bucket=hot, score≥80, recommended_action=call_immediately
```

---

## Caveats & Gaps

- **Postgres hosting decision (Sprint 1):** Aurora Postgres vs self-managed on EC2. This affects `DATABASE_URL` format and whether `DATABASE_SSL_MODE` needs to be set differently. Both are compatible with the asyncpg driver and SQLAlchemy ORM.
- **Orchestration tool decision (Sprint 1):** Inngest vs Temporal. The env vars in §2.5 cover both. The `inngest-function-design.md` has TypeScript implementations; Python SDK translations are needed if Python is confirmed as the sole language. Inngest Python SDK supports identical step semantics.
- **Real-time delivery (Sprint 1):** Pusher vs Soketi affects env vars not listed here (WebSocket connection URL, channel key, auth secret). These will be added once the decision is made. Not on the critical path for Pipeline 1 correctness.
- **Test tenant seed data:** The `manage.py seed` command is a placeholder. The seed script must create: `test-tenant-001` with locked `PersonaObject`, scoring weights, 10 pre-defined signals, and `prompt_template_version = "v1.0.0-test"`. See [[analyses/test-strategy]] §Test Data for full spec.
- **Google Sheets connector:** Setup steps for Google OAuth (service account vs OAuth 2.0 flow) are not covered here. Defer to Sprint 2 when the Sheets import path is implemented.
- **IndiaMART / JustDial API access:** Both require business verification before API keys are issued. Request credentials before Sprint 2 to avoid blocking the enrichment fallback chain.

## Follow-up Questions

- Which team member manages AWS IAM and can provision dev credentials for new developers?
- Should `APP_ENV=development` skip Secrets Manager entirely (read all secrets from `.env`), or always attempt Secrets Manager with `.env` as fallback?
- Is there a shared dev Clerk organization already configured, or does each developer create their own?
