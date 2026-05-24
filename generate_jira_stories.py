#!/usr/bin/env python3
"""
Jira Story Generator — Multi-Tenant Adaptive Lead Intelligence Engine
Outputs: jira_stories.csv (Jira-importable) + jira_stories.xlsx (formatted)

Import rules baked in:
  - Issue ID: sequential integers (Jira assigns keys on import)
  - Epic rows:  Epic Name = <name>, Epic Link = ""
  - Story rows: Epic Name = "",    Epic Link = <epic name string>
  - Acceptance Criteria embedded in Description under ## Acceptance Criteria
  - Blocks: Issue ID of the issue this story blocks (A.Blocks=B means B cannot start until A is done)
"""

import csv
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    print("WARNING: openpyxl not available — XLSX output skipped")

OUTPUT_DIR = Path(r"C:\Users\anish\Desktop\POC\GamoftXpoc")

COLUMNS = [
    "Issue ID", "Issue Type", "Summary", "Description",
    "Epic Name", "Epic Link", "Sprint", "Assignee",
    "Priority", "Story Points", "Labels", "Blocks", "Components",
]

rows: list[dict] = []


def add(
    issue_type: str,
    summary: str,
    description: str,
    epic_name: str = "",
    epic_link: str = "",
    sprint: str = "",
    assignee: str = "",
    priority: str = "Medium",
    story_points: int | str = "",
    labels: str = "",
    components: str = "",
) -> dict:
    r: dict = {
        "Issue ID": len(rows) + 1,
        "Issue Type": issue_type,
        "Summary": summary,
        "Description": description,
        "Epic Name": epic_name,
        "Epic Link": epic_link,
        "Sprint": sprint,
        "Assignee": assignee,
        "Priority": priority,
        "Story Points": story_points,
        "Labels": labels,
        "Blocks": "",
        "Components": components,
    }
    rows.append(r)
    return r


def ac(overview: str, items: list[str]) -> str:
    bullets = "\n".join(f"- {i}" for i in items)
    return f"{overview}\n\n## Acceptance Criteria\n{bullets}"


# ─────────────────────────────────────────────────────────────
# EPIC NAME CONSTANTS  (must match exactly in Epic Link fields)
# ─────────────────────────────────────────────────────────────
E1 = "Foundation & Infrastructure"
E2 = "Tenant Onboarding"
E3 = "Lead Ingestion"
E4 = "Lead Scoring"
E5 = "Delivery & Salesperson UI"
E6 = "Feedback Loop"
E7 = "Security Hardening"
E8 = "Observability & CI/CD"
E9 = "Testing & Validation"

# ═══════════════════════════════════════════════════════════════
# EPICS  (Epic Name set; Epic Link intentionally blank)
# ═══════════════════════════════════════════════════════════════
e1 = add("Epic", E1,
         "Foundation: database schema (33 entities), FastAPI scaffold (8 services), Clerk JWT auth, 4-role RBAC, LiteLLM proxy, workflow orchestration, structured logging, CI pipeline.",
         epic_name=E1, sprint="Sprint 1", priority="Highest",
         labels="foundation,infrastructure", components="Infrastructure")

e2 = add("Epic", E2,
         "Pipeline 2 (runs once per tenant): Persona Agent, ICP Agent, Signal Agent configuration via Sonnet 4.6. Prompt registry, prompt versioning, PersonaObject TTLCache.",
         epic_name=E2, sprint="Sprint 2", priority="High",
         labels="onboarding,pipeline-2", components="Onboarding")

e3 = add("Epic", E3,
         "Lead ingestion across all channels: WhatsApp DM, Instagram DM, Facebook DM, Facebook Lead Ads (3 surfaces), email inbound, CSV/Google Sheets bulk upload.",
         epic_name=E3, sprint="Sprint 3", priority="High",
         labels="ingestion,pipeline-1", components="Ingestion")

e4 = add("Epic", E4,
         "Pipeline 1 scoring stages: enrichment (9 providers), signal extraction (13 types), normalisation, disqualification gate, Rating Agent (Sonnet 4.6), Output Schema Layer, lineage audit, score decay.",
         epic_name=E4, sprint="Sprint 4", priority="Highest",
         labels="scoring,pipeline-1,llm", components="Scoring")

e5 = add("Epic", E5,
         "Real-time lead card delivery, HOT push notifications, human review queue UI, role-scoped dashboards, CRM sync (Salesforce + HubSpot), outbound webhooks.",
         epic_name=E5, sprint="Sprint 5", priority="High",
         labels="delivery,ui", components="Delivery,UI")

e6 = add("Epic", E6,
         "Feedback collection API, outcome attribution, pattern detection, quality snapshots, AP/C/AR metrics, admin CLI suite (5 commands).",
         epic_name=E6, sprint="Sprint 6", priority="Medium",
         labels="feedback,quality", components="Feedback")

e7 = add("Epic", E7,
         "Security hardening: PII field audit, AES-256-GCM enforcement, RBAC audit, cross-tenant RLS adversarial tests, webhook replay protection, session hardening.",
         epic_name=E7, sprint="Sprint 6", priority="High",
         labels="security,compliance", components="Security")

e8 = add("Epic", E8,
         "CloudWatch dashboards, alert thresholds, autoscaling (3 services), runbook. CI/CD staging + production promotion gates, automated DB backups, correlation_id audit.",
         epic_name=E8, sprint="Sprint 7", priority="High",
         labels="observability,ci-cd", components="Observability,DevOps")

e9 = add("Epic", E9,
         "E2E golden path tests (HOT B2B, COLD SMB, NOISE), LLM evaluation suite (5 agents × 20 cases), full test coverage audit, Govmen tenant onboarding.",
         epic_name=E9, sprint="Sprint 7", priority="High",
         labels="testing,validation", components="QA")

# ═══════════════════════════════════════════════════════════════
# PREREQUISITES  (no sprint — must be done before sprints begin)
# ═══════════════════════════════════════════════════════════════
p_meta = add("Task",
    "Register Meta Developer App and submit for Business Verification (BLOCKER)",
    ac(
        "Register on Meta for Developers. Submit for Business Verification and app review. "
        "CRITICAL: Business Verification can take up to 60 days. App review takes 2–7 days for a clean submission. "
        "Do NOT wait — start immediately. This is a hard prerequisite for Sprint 3 ingestion work.",
        [
            "Meta Developer App created at developers.facebook.com",
            "WABA (WhatsApp Business Account) registered and linked to the app",
            "Business Verification documents submitted to Meta",
            "App review submitted for WhatsApp, Instagram, and Facebook Lead Ads permissions",
            "Instagram OAuth app permissions and scopes confirmed",
            "Facebook Lead Ads permissions approved (or in review)",
            "All approval statuses tracked; any delays escalated to team before Sprint 3 begins",
        ]
    ),
    sprint="", assignee="Dev A", priority="Highest",
    labels="prerequisite,meta,blocker", components="Ingestion")

p_enrichment_apis = add("Task",
    "Obtain API keys for all 9 enrichment providers and store in AWS Secrets Manager",
    ac(
        "Register and obtain API credentials for every enrichment provider before Sprint 4. "
        "All keys must be stored in AWS Secrets Manager under /lead-engine/enrichment/ before Dev A begins enrichment service work.",
        [
            "Truecaller Business API: key obtained and stored",
            "Apollo.io API: key obtained and stored",
            "Surepass API: key obtained and stored",
            "Probe42 API: key obtained and stored",
            "Tracxn API: key obtained and stored",
            "NewsCatcherAPI: subscription active, key stored",
            "Serper.dev API: key obtained and stored",
            "Google Places API: key obtained and stored",
            "IndiaMART/JustDial: API access obtained OR scraping limitation documented with decision memo",
            "All keys stored in AWS Secrets Manager under /lead-engine/enrichment/<provider>",
            "Rate limits, quotas, and per-call costs documented for each provider",
        ]
    ),
    sprint="", assignee="Dev C", priority="Highest",
    labels="prerequisite,enrichment,blocker", components="Enrichment,Infrastructure")

p_indiamrt = add("Task",
    "Investigate IndiaMART and JustDial API access — business verification and lead time",
    ac(
        "Apply for IndiaMART and JustDial B2B lead data API access. Both require business verification. "
        "Confirm whether scraping restrictions apply. Decision memo must be written before Sprint 4 begins.",
        [
            "Business verification submitted to IndiaMART and JustDial portals",
            "API credentials obtained OR access limitation formally documented",
            "Decision recorded: API vs scraping vs skip for POC",
            "Scraping restriction analysis complete (ToS reviewed)",
            "Decision memo written and communicated to team",
            "Lead time confirmed; no Sprint 4 work blocked",
        ]
    ),
    sprint="", assignee="Dev A", priority="Highest",
    labels="prerequisite,enrichment,blocker", components="Enrichment")

p_clerk = add("Task",
    "Set up Clerk account, configure JWT templates with tenant_id + role claims, define 4-role RBAC",
    ac(
        "Create the Clerk project for the Lead Intelligence Engine. Configure JWT templates to emit "
        "tenant_id and role claims — both required by RLS policies and RBAC middleware. "
        "Must be done before Sprint 1 Dev B work begins.",
        [
            "Clerk project created with correct application name",
            "JWT template includes tenant_id (UUID) and role (admin|team_lead|salesperson|viewer) claims",
            "4 roles defined in Clerk dashboard: admin, team_lead, salesperson, viewer",
            "JWKS public key endpoint URL confirmed and accessible",
            "JWKS public key stored in AWS Secrets Manager under /lead-engine/auth/clerk-jwks",
            "Clerk dashboard access shared with all three developers",
            "Test JWT generated and manually verified to contain correct claims",
        ]
    ),
    sprint="", assignee="Dev B", priority="Highest",
    labels="prerequisite,auth,blocker", components="Infrastructure,Auth")

p_aws = add("Task",
    "Provision AWS account: ECS Fargate cluster, CloudWatch, Secrets Manager, ECR repositories",
    ac(
        "Provision all required AWS infrastructure for the Lead Intelligence Engine. "
        "IAM roles must follow least-privilege principle. Must be complete before Sprint 1 begins.",
        [
            "ECS Fargate cluster provisioned in target region",
            "CloudWatch log groups created per service (8 groups: ingestion, enrichment, profile, scoring, orchestration, reporting, feedback, onboarding)",
            "AWS Secrets Manager namespace /lead-engine/ created with dev/staging/prod paths",
            "ECR repositories created for all 8 service Docker images",
            "IAM task execution roles with least-privilege policies attached to each service",
            "IAM role for CI/CD pipeline with ECR push + ECS deploy permissions",
            "AWS credentials securely distributed to all three developers",
            "VPC with private subnets configured for ECS tasks",
        ]
    ),
    sprint="", assignee="Dev C", priority="Highest",
    labels="prerequisite,aws,blocker", components="Infrastructure")

# ═══════════════════════════════════════════════════════════════
# SPRINT 1 — SPIKES  (decisions must be locked by end of Sprint 1)
# ═══════════════════════════════════════════════════════════════
sp_inngest = add("Story",
    "[SPIKE] Workflow Orchestration: Inngest vs Temporal — Decision Required by Sprint 1 Day 3",
    ac(
        "Evaluate Inngest vs Temporal for Pipeline 1 workflow orchestration. "
        "The chosen engine must support: step retries, waitForEvent (for awaiting_clarification 24h timeout), "
        "crash recovery (resume from last successful stage), and ECS Fargate deployment. "
        "Dev C must lock this decision by Sprint 1 Day 3 so workflow wiring story can begin.",
        [
            "Both options evaluated against: local dev experience, Python SDK maturity, step retry semantics",
            "waitForEvent support verified for both options (needed for 24h clarification timeout)",
            "Crash recovery semantics verified: can pipeline resume from last successful step?",
            "ECS Fargate deploy complexity assessed for each option",
            "Docker Compose local dev story assessed (self-contained vs cloud dependency)",
            "Cost at POC scale (3 tenants, ~10k leads/month) estimated",
            "Decision memo written with recommendation and rationale",
            "Decision communicated to all developers and locked by Sprint 1 Day 3",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev C", priority="Highest",
    story_points=3, labels="spike,decision,orchestration", components="Infrastructure")

sp_aurora = add("Story",
    "[SPIKE] PostgreSQL Hosting: Aurora Serverless v2 vs EC2 RDS — Decision Required by Sprint 1 Day 2",
    ac(
        "Evaluate Aurora Serverless v2 vs EC2 self-managed PostgreSQL. "
        "Decision must be locked by Sprint 1 Day 2 — Dev A's schema work cannot begin until DB host is confirmed.",
        [
            "Both options evaluated against: RLS row-level security compatibility, Alembic migration support",
            "Connection pooling strategy defined (pgBouncer vs RDS Proxy vs none at POC scale)",
            "Cold start latency assessed for Aurora Serverless v2 under POC load",
            "Cost estimate at POC scale (3 tenants, <100k rows) documented",
            "Operational burden assessed: backups, failover, upgrades",
            "Decision memo written and locked by Sprint 1 Day 2",
            "Decision communicated to Dev A immediately so schema work can begin",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev A", priority="Highest",
    story_points=3, labels="spike,decision,database", components="Infrastructure")

sp_pusher = add("Story",
    "[SPIKE] Real-time Lead Delivery: Pusher vs Soketi — Decision Required by Sprint 1 Day 5",
    ac(
        "Evaluate Pusher (managed) vs Soketi (self-hosted, Pusher-compatible) for real-time push to salesperson UI. "
        "Decision needed before Sprint 5 delivery work but should be confirmed in Sprint 1 to avoid late rework.",
        [
            "Both options evaluated against: POC cost, channel isolation per tenant, SDK compatibility",
            "Soketi self-hosted Fargate deploy complexity assessed (Docker image, config, persistence)",
            "Pusher POC pricing estimated at 3 tenants × expected concurrent connections",
            "Channel-per-tenant isolation model validated for both options",
            "Connection limits at POC scale assessed",
            "Decision memo written and locked by Sprint 1 Day 5",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev B", priority="High",
    story_points=3, labels="spike,decision,realtime", components="Infrastructure,Delivery")

# ═══════════════════════════════════════════════════════════════
# SPRINT 1 — FOUNDATION & INFRASTRUCTURE (Epic 1)
# Dev A: DB schema + RLS   |   Dev B: FastAPI + Clerk RBAC   |   Dev C: LiteLLM + orchestration + CI
# ═══════════════════════════════════════════════════════════════

s1_schema = add("Story",
    "Design and implement PostgreSQL schema for all 33 entities with Alembic migrations",
    ac(
        "Implement the complete database schema. All 33 entities created with correct types, constraints, "
        "foreign keys, indexes, and multi-tenancy (tenant_id on every table). Alembic configured for all 8 services. "
        "Begins only after Aurora vs EC2 spike decision is locked.",
        [
            "All 33 entities created: tenant, lead_record, pipeline_stage, pipeline_run, task_execution, "
            "lineage_record, intake_event_log, enrichment_record, enrichment_quota, signal_scores, lead_score, "
            "feedback_record, quality_metrics, enrichment_health_snapshot, prompt_registry, tenant_config, "
            "persona_object, icp_profile, signal_config, notification_record, crm_sync_record, "
            "webhook_registration, webhook_delivery_log, outbound_event_log, sla_breach_log, "
            "failed_audit_log, daily_enrichment_health_snapshot, recommendations, admin_cli_log, "
            "user_account, role_assignment, session_log, config_history",
            "Every table includes: tenant_id UUID NOT NULL FK, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ",
            "PipelineStage enum column covers all 10 values: captured, fetched, enriched, normalised, "
            "scored, delivered, existing_customer, human_review, awaiting_clarification, insufficient_signal, failed",
            "Alembic configured: env.py reads DB URL from env var; shared migration history across 8 services",
            "Migration runs cleanly from zero: `alembic upgrade head` with no errors",
            "Indexes created on: (tenant_id, created_at), (tenant_id, pipeline_stage), all FK columns",
            "5-year retention annotation on: lineage_record, pipeline_stage, failed_audit_log tables",
            "Schema ER diagram committed to docs/ directory",
            "Migration tested on both local Docker Compose Postgres and target hosted DB",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev A", priority="Highest",
    story_points=13, labels="database,schema,foundation,sprint1", components="Infrastructure,Database")

s1_rls = add("Story",
    "Implement PostgreSQL Row-Level Security (RLS) policies for all tenant-scoped tables",
    ac(
        "Enable and configure RLS on all 33 tenant-scoped tables. Uses app.tenant_id session variable "
        "set by the application on each DB connection. Requires Clerk JWT middleware (Dev B) to be in place first "
        "because RLS depends on tenant_id being propagated from the JWT.",
        [
            "RLS enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) on all 33 tables",
            "SELECT policy: USING (tenant_id = current_setting('app.tenant_id')::uuid)",
            "INSERT policy: WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)",
            "UPDATE/DELETE policies equivalent",
            "Application DB role does NOT have superuser — cannot bypass RLS",
            "Superuser-only admin role documented (for migrations only)",
            "Adversarial test: 3 tenants; tenant A JWT cannot read tenant B rows — returns 0 rows",
            "Adversarial test: tenant A JWT cannot write to tenant B rows — raises RLS violation",
            "All RLS policies version-controlled in Alembic migration (not applied manually)",
            "Unit tests for each policy type using 3 synthetic tenants",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev A", priority="Highest",
    story_points=8, labels="security,rls,database,foundation,sprint1", components="Infrastructure,Database,Security")

s1_fastapi = add("Story",
    "Scaffold all 8 FastAPI microservices with shared Pydantic models and Docker Compose",
    ac(
        "Create the FastAPI application skeleton for all 8 services. Shared Pydantic models are "
        "the contract for all inter-service communication and are consumed by all Sprint 2+ stories. "
        "This story is the single highest-dependency item in Sprint 1.",
        [
            "8 services scaffolded: ingestion, enrichment, profile, scoring, orchestration, reporting, feedback, onboarding",
            "Each service has: main.py, router/, schemas/, models/, services/, tests/ structure",
            "Each service exposes GET /health → {status: ok, service: <name>, version: <git_sha>}",
            "Shared package `lead_engine_shared`: installable via `uv add lead-engine-shared`",
            "Shared Pydantic models: LeadRecord, TenantConfig, InboundMessage, LeadScore, EnrichedLeadRecord",
            "PipelineStage: Literal enum covering all 10 stage values",
            "DisqualRule TypedDict: {condition_type: Literal[...], effect: Literal['score_cap','score_delta','force_zero'], value: int, reason_label: str}",
            "All 8 services import PipelineStage and LeadRecord from shared package (zero duplication)",
            "Docker Compose file: all 8 services + Postgres + LiteLLM proxy run with `docker compose up`",
            "Hot-reload enabled in Docker Compose for local development",
            "Each service has pyproject.toml with uv; Python 3.12 pinned",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev B", priority="Highest",
    story_points=13, labels="api,scaffold,pydantic,foundation,sprint1", components="Infrastructure,API")

s1_clerk = add("Story",
    "Implement Clerk JWT middleware and 4-role RBAC across all 8 FastAPI services",
    ac(
        "Integrate Clerk JWT verification into all 8 FastAPI services via shared middleware. "
        "Middleware extracts tenant_id and role from JWT, sets app.tenant_id on the DB session for RLS. "
        "Depends on shared Pydantic models (s1_fastapi) being in place.",
        [
            "Clerk JWKS verification middleware implemented using PyJWT + Clerk JWKS endpoint",
            "Middleware registered on all 8 services as a FastAPI dependency",
            "Middleware sets app.tenant_id on DB session: `SET LOCAL app.tenant_id = '<uuid>'`",
            "Middleware extracts: tenant_id (UUID), role (str), user_id (str) from JWT claims",
            "4 role decorators: @require_role('admin'), @require_role('team_lead'), @require_role('salesperson'), @require_role('viewer')",
            "viewer: GET endpoints only on own tenant resources",
            "salesperson: GET + POST /feedback on own tenant; cannot access config",
            "team_lead: GET all leads + POST /assignments on own tenant; cannot change config",
            "admin: full CRUD including tenant config and user management on own tenant",
            "Unauthenticated request → 401 Unauthorized",
            "Wrong-role request → 403 Forbidden with reason string",
            "Expired JWT → 401 with error: token_expired",
            "Unit tests: each of the 4 role boundaries + expired token + missing token",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev B", priority="Highest",
    story_points=8, labels="auth,rbac,clerk,foundation,sprint1", components="Infrastructure,Auth,Security")

s1_litellm = add("Story",
    "Configure LiteLLM proxy for Anthropic Claude and OpenAI with per-tenant concurrency cap",
    ac(
        "Set up LiteLLM proxy as a sidecar service. Routes all LLM calls from all 8 services. "
        "Enforces per-tenant concurrency cap (default: 5 concurrent Scoring Agent calls). "
        "API keys sourced from AWS Secrets Manager — never hardcoded.",
        [
            "LiteLLM proxy deployed as Docker Compose service on port 4000",
            "claude-sonnet-4-6 routed for: Rating Agent, Persona Agent, ICP Agent, Signal Agent",
            "claude-haiku-4-5-20251001 routed for: Message Parser only",
            "gpt-4o configured as fallback router via LiteLLM (activates on Anthropic 5xx only)",
            "Anthropic API key loaded from AWS Secrets Manager at startup",
            "OpenAI API key loaded from AWS Secrets Manager at startup",
            "Per-tenant concurrency cap enforced: default 5; reads tenant_config.concurrency_cap",
            "LiteLLM request log: {model, tenant_id_hash, latency_ms, tokens_in, tokens_out} → CloudWatch",
            "Zero PII in LiteLLM logs (tenant_id logged as SHA-256 hash only)",
            "GET /health on LiteLLM proxy returns model availability status",
            "All 8 services configure LiteLLM base URL from env var LITELLM_BASE_URL",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev C", priority="High",
    story_points=8, labels="llm,litellm,foundation,sprint1", components="Infrastructure,LLM")

s1_orchestration = add("Story",
    "Wire workflow orchestration engine and implement structured JSON logging with correlation IDs",
    ac(
        "Integrate the chosen workflow engine (Inngest or Temporal — locked by Sprint 1 Day 3 spike). "
        "All Pipeline 1 stage transitions must be representable as workflow steps. "
        "Structured JSON logging with correlation_id propagation is consumed by every subsequent story.",
        [
            "Workflow engine client installed and configured (Inngest SDK or Temporal SDK per spike decision)",
            "Pipeline 1 stage transitions modelled as workflow steps: captured→fetched→enriched→normalised→scored→terminal",
            "waitForEvent step implemented: used for awaiting_clarification 24h timeout",
            "Crash recovery: workflow resumes from last successful pipeline_stage row on service restart",
            "Dead letter step: on step failure after 3 retries, transition to failed and emit CRITICAL metric",
            "Structured JSON log format: {timestamp, service, level, correlation_id, tenant_id_hash, message, extra}",
            "correlation_id: UUID generated at ingestion entry; propagated via X-Correlation-ID header to all downstream HTTP calls",
            "tenant_id logged as SHA-256 hash only — never plaintext in logs",
            "Log shipping configured to CloudWatch Logs /lead-engine/<service>/",
            "All 8 services use shared logging module from lead_engine_shared package",
            "Integration test: submit synthetic lead, verify correlation_id appears in logs of all services touched",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev C", priority="Highest",
    story_points=8, labels="orchestration,logging,correlation-id,foundation,sprint1", components="Infrastructure,Orchestration")

s1_ci = add("Story",
    "Set up GitHub Actions CI pipeline with lint, type-check, test, and Docker build gates",
    ac(
        "Configure GitHub Actions for all 8 services. Every PR must pass all gates before merge is allowed.",
        [
            "GitHub Actions workflow runs on every PR and push to main",
            "Gate 1 — ruff lint: zero errors required across all 8 services",
            "Gate 2 — mypy strict: zero type errors required across all 8 services",
            "Gate 3 — pytest: all existing tests pass; test collection must not error",
            "Gate 4 — Docker build: all 8 service images build successfully",
            "Failing any gate blocks the PR merge",
            "CI workflow uses uv for fast dependency installation",
            "Matrix strategy: each service tested in parallel (not sequentially)",
            "CI run time target: under 5 minutes for full suite",
            "Branch protection rules configured on main: require CI pass + 1 reviewer",
        ]
    ),
    epic_link=E1, sprint="Sprint 1", assignee="Dev C", priority="High",
    story_points=5, labels="ci,devops,foundation,sprint1", components="DevOps")

# ═══════════════════════════════════════════════════════════════
# SPRINT 2 — TENANT ONBOARDING (Epic 2)
# Dev A: Onboarding API + queue drain   |   Dev B: Persona + ICP + Signal agents   |   Dev C: Prompt registry + TTLCache
# ═══════════════════════════════════════════════════════════════

s2_onboarding_api = add("Story",
    "Implement tenant onboarding API: CRUD endpoints, JSONB config storage, tenant status lifecycle",
    ac(
        "Build the onboarding REST API for Pipeline 2. Tenant status lifecycle: draft → configured → active → suspended. "
        "DisqualRule[] stored in JSONB and validated against TypedDict schema on every PUT.",
        [
            "POST /tenants: creates tenant with status=draft; admin role required",
            "PUT /tenants/{id}/config: validates and stores config JSONB; transitions status draft→configured",
            "Config JSONB fields: business_type, target_market, icp_criteria, disqualification_rules (DisqualRule[]), concurrency_cap (default 5), enrichment_providers (list)",
            "DisqualRule validation: each rule must have condition_type (Literal), effect (Literal: score_cap|score_delta|force_zero), value (int), reason_label (str)",
            "GET /tenants/{id}/status: returns {status, config_version, pipeline2_complete, activated_at}",
            "PUT /tenants/{id}/suspend: admin role; transitions active→suspended; stops queue drain",
            "Config versioning: each PUT /config increments version integer; stores previous version in config_history table",
            "GET /tenants/{id}/config/history: returns list of previous versions",
            "PUT /tenants/{id}/config/rollback?version=N: admin role; rolls back to version N",
            "All endpoints documented in OpenAPI spec (auto-generated by FastAPI)",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev A", priority="High",
    story_points=8, labels="onboarding,api,pipeline-2,sprint2", components="Onboarding,API")

s2_queue_drain = add("Story",
    "Implement queue drain on tenant activation and lead backlog processing",
    ac(
        "When a tenant transitions configured→active (after Pipeline 2 completes), trigger queue drain "
        "to pick up any leads captured during the onboarding window.",
        [
            "POST /tenants/{id}/activate: triggers queue drain; transitions configured→active",
            "Queue drain: queries lead_record for this tenant where pipeline_stage=captured and created_at < activation_time",
            "Each backlog lead enqueued in workflow engine for Pipeline 1 processing",
            "Concurrency cap respected during drain (default 5 concurrent scoring calls per tenant)",
            "Drain status logged: {tenant_id, lead_count_drained, started_at, completed_at}",
            "Re-activation guard: if tenant already active, POST /activate returns 409 with message",
            "Drain is idempotent: re-triggering does not double-enqueue leads already in processing",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev A", priority="Medium",
    story_points=5, labels="onboarding,queue,pipeline-2,sprint2", components="Onboarding")

s2_persona_agent = add("Story",
    "Implement Persona Agent (Pipeline 2) — tenant persona synthesis via claude-sonnet-4-6",
    ac(
        "Build the Persona Agent for Pipeline 2. Runs once at tenant onboarding. Reads tenant config and "
        "synthesizes a PersonaObject. Uses claude-sonnet-4-6 via LiteLLM. "
        "Prompt stored in prompt_registry at version v1.0.0.",
        [
            "Persona Agent implemented as async LiteLLM call to claude-sonnet-4-6",
            "Input: TenantOnboardingInput {business_type, target_market, example_customers: list[str], notes: str}",
            "Output: PersonaObject {icp_attributes: dict[str, str], customer_journey: str, pain_points: list[str], comm_style: str, confidence: float}",
            "Output validated with Pydantic before storage; invalid output retried (max 2 retries)",
            "PersonaObject stored in tenant_config JSONB under key 'persona'",
            "Prompt stored in prompt_registry: name='persona_agent', version='v1.0.0', is_active=True",
            "Prompt fetched from registry at call time (not hardcoded)",
            "LLM call logged to task_execution: {agent='persona_agent', tenant_id, tokens_in, tokens_out, latency_ms, success}",
            "On LLM failure after 3 retries: tenant onboarding marked pipeline2_status=failed; admin alerted",
            "Unit tests: valid input → valid PersonaObject schema; LLM error → retry then fail gracefully",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev B", priority="High",
    story_points=8, labels="llm,persona-agent,pipeline-2,sprint2", components="Onboarding,LLM")

s2_icp_agent = add("Story",
    "Implement ICP Agent (Pipeline 2) — Ideal Customer Profile generation via claude-sonnet-4-6",
    ac(
        "Build the ICP Agent for Pipeline 2. Runs after Persona Agent completes. "
        "Uses PersonaObject + tenant ICP criteria to generate a structured ICPProfile with signal weights.",
        [
            "ICP Agent implemented as async LiteLLM call to claude-sonnet-4-6",
            "Input: ICPAgentInput {persona_object: PersonaObject, icp_criteria: dict} (fetched from tenant_config)",
            "Output: ICPProfile {signal_weights: dict[SignalType, float], score_thresholds: {hot: int, warm: int}, tier_labels: dict}",
            "signal_weights values sum to 1.0 (validated; if not, normalized before storage)",
            "ICPProfile stored in tenant_config JSONB under key 'icp_profile'",
            "Prompt stored in prompt_registry: name='icp_agent', version='v1.0.0', is_active=True",
            "ICP Agent runs only after Persona Agent succeeds (sequential — checks pipeline2_status)",
            "LLM call logged to task_execution",
            "On failure after 3 retries: pipeline2_status=failed; admin alerted",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev B", priority="High",
    story_points=8, labels="llm,icp-agent,pipeline-2,sprint2", components="Onboarding,LLM")

s2_signal_agent = add("Story",
    "Implement Signal Agent (Pipeline 2) — signal extraction config generation via claude-sonnet-4-6",
    ac(
        "Build the Signal Agent for Pipeline 2. Runs after ICP Agent completes. "
        "Generates per-tenant signal extraction configuration: which of the 13 signal types to activate, "
        "weight multipliers, and intent keyword lists.",
        [
            "Signal Agent implemented as async LiteLLM call to claude-sonnet-4-6",
            "Input: SignalAgentInput {icp_profile: ICPProfile, tenant_context: dict}",
            "Output: SignalConfig {active_signals: list[SignalType], weight_multipliers: dict[SignalType, float], intent_keywords: list[str]}",
            "All 13 SignalType values available: intent, urgency, authority, budget, timeline, engagement, recency, channel_fit, geographic_fit, company_size_fit, role_fit, industry_fit, behavioral",
            "SignalConfig stored in tenant_config JSONB under key 'signal_config'",
            "On SignalConfig stored: tenant pipeline2_status set to 'complete'",
            "pipeline2_complete=True triggers POST /tenants/{id}/activate call (queue drain starts)",
            "Prompt stored in prompt_registry: name='signal_agent', version='v1.0.0', is_active=True",
            "Signal Agent runs only after ICP Agent succeeds",
            "LLM call logged to task_execution",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev B", priority="High",
    story_points=8, labels="llm,signal-agent,pipeline-2,sprint2", components="Onboarding,LLM")

s2_prompt_registry = add("Story",
    "Implement prompt_registry service: versioning, evaluation framework, promote, and rollback",
    ac(
        "Build the prompt registry service. All 5 LLM agent prompts stored with semantic versions. "
        "Prompt changes require evaluation before promotion. Rollback to previous version supported.",
        [
            "prompt_registry table: (id, prompt_name, version, content, model, temperature, max_tokens, created_at, is_active)",
            "Seed script: all 5 agent prompts at v1.0.0 (persona_agent, icp_agent, signal_agent, rating_agent, message_parser)",
            "GET /prompts/{name}/active: returns current active prompt + version",
            "POST /prompts/{name}/versions: creates new version (is_active=False by default)",
            "POST /prompts/{name}/promote?version=X: sets version X active; deactivates current; rejects if evaluation not run",
            "POST /prompts/{name}/rollback?version=X: rolls back to version X; deactivates current",
            "Evaluation framework: POST /prompts/{name}/evaluate?version=X runs 20 pre-defined test cases",
            "Evaluation gate: ≥90% schema validity rate required before promotion is allowed",
            "All Pipeline 1/2 agents fetch prompt from registry at call time; no hardcoded prompts anywhere",
            "Prompt change audit log: every promote/rollback writes to admin_cli_log with user_id and reason",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev C", priority="High",
    story_points=8, labels="prompts,registry,versioning,sprint2", components="Onboarding,LLM")

s2_ttlcache = add("Story",
    "Implement PersonaObject TTLCache and Rating Agent prompt assembly with per-tenant context injection",
    ac(
        "Implement in-memory TTLCache for PersonaObject per tenant to reduce DB reads during Pipeline 1. "
        "Also implement prompt assembly: at scoring time, inject PersonaObject and ICPProfile into "
        "Rating Agent template from prompt_registry.",
        [
            "TTLCache implemented using cachetools.TTLCache; TTL=300 seconds; max_size=100 tenants",
            "Cache key: tenant_id (UUID string)",
            "Cache miss: reads PersonaObject from tenant_config JSONB; populates cache",
            "Cache invalidation: PUT /tenants/{id}/config sends internal cache-bust event; cache entry evicted",
            "Prompt assembly function: fetches active rating_agent template from registry; injects {persona_object_json} and {icp_profile_json} placeholders",
            "Assembled prompt is an ephemeral instance — template version is what's versioned, not the assembled instance",
            "Unit test — cache hit: second call within TTL reads from cache (zero DB queries)",
            "Unit test — cache miss: first call hits DB and populates cache",
            "Unit test — cache invalidation: after PUT /config, next call reads fresh from DB",
            "Benchmark: cache hit p99 latency < 1ms",
        ]
    ),
    epic_link=E2, sprint="Sprint 2", assignee="Dev C", priority="Medium",
    story_points=5, labels="cache,prompts,pipeline-1,sprint2", components="Onboarding,LLM")

# ═══════════════════════════════════════════════════════════════
# SPRINT 3 — LEAD INGESTION (Epic 3)
# Dev A: Meta webhook + WhatsApp/Instagram   |   Dev B: Facebook/Lead Ads + email/CSV   |   Dev C: Message Parser + filter/dedup
# ═══════════════════════════════════════════════════════════════

s3_meta_webhook = add("Story",
    "Implement Meta webhook receiver: HMAC-SHA256 validation, challenge-response, intake_event_log",
    ac(
        "Build the shared Meta webhook receiver endpoint. All Meta-origin events (WhatsApp, Instagram, Facebook) "
        "arrive here. HMAC-SHA256 verification is the first gate — invalid signatures are rejected immediately. "
        "Raw payload stored to intake_event_log before any downstream processing.",
        [
            "POST /webhooks/meta endpoint implemented in ingestion service",
            "HMAC-SHA256 signature verified on X-Hub-Signature-256 header using webhook secret from Secrets Manager",
            "Invalid signature → 403 Forbidden; no payload stored",
            "Replay protection: webhook timestamp compared to server time; diff > 5 minutes → 403",
            "GET /webhooks/meta: handles Meta hub.challenge verification (echo hub.challenge param)",
            "Endpoint returns HTTP 200 immediately after signature check; all processing is async",
            "Response latency < 200ms (Meta will retry if no 200 within timeout)",
            "Raw JSON payload stored to intake_event_log: {id, received_at, source='meta', raw_payload, signature_valid, processing_status='pending'}",
            "Webhook secret rotated monthly; rotation does not require service restart (reads from Secrets Manager on each request)",
            "Load test: handle 100 concurrent webhook deliveries without dropping any",
        ]
    ),
    epic_link=E3, sprint="Sprint 3", assignee="Dev A", priority="Highest",
    story_points=8, labels="ingestion,meta,webhook,security,sprint3", components="Ingestion")

s3_whatsapp_instagram = add("Story",
    "Implement WhatsApp DM and Instagram DM lead capture with 60-day token refresh and polling fallback",
    ac(
        "Process WhatsApp and Instagram DM messages from the Meta webhook payload. "
        "Both channels create LeadRecord with pipeline_stage=captured. "
        "Instagram OAuth token must be refreshed every 60 days; polling fallback activates if webhook delivery fails.",
        [
            "WhatsApp DM processor: extracts phone (wa_id), message_body, waba_message_id, timestamp from webhook payload",
            "LeadRecord created: source=whatsapp, pipeline_stage=captured, raw_message stored, external_id=waba_message_id",
            "Instagram OAuth flow: GET /auth/instagram/callback handles redirect; stores long-lived access token encrypted in DB",
            "Instagram token refresh job: cron runs daily at 03:00 UTC; refreshes tokens expiring within 7 days",
            "Instagram DM processor: extracts sender_igsid, message_body, timestamp from webhook payload",
            "LeadRecord created: source=instagram, pipeline_stage=captured, external_id=instagram_message_id",
            "Polling fallback: if webhook delivery for a tenant fails 3 consecutive times, switch tenant to polling mode (GET /messages every 15 minutes)",
            "Polling fallback resets to webhook mode when webhook delivery resumes",
            "Deduplication: same external_id → silently skip (no duplicate LeadRecord); log as 'duplicate_skipped'",
            "Failed lead creation: log to intake_event_log with processing_status='failed' and error details",
        ]
    ),
    epic_link=E3, sprint="Sprint 3", assignee="Dev A", priority="High",
    story_points=10, labels="ingestion,whatsapp,instagram,sprint3", components="Ingestion")

s3_facebook_leadads = add("Story",
    "Implement Facebook DM and Lead Ads ingestion across all 3 Lead Ads surfaces",
    ac(
        "Process Facebook DM messages and Lead Ads form submissions. "
        "Lead Ads has 3 surfaces: native form, Instant Experience, and Messenger. "
        "All normalise to the same LeadRecord schema.",
        [
            "Facebook DM processor: extracts sender PSID, message_body, page_id, timestamp",
            "LeadRecord created: source=facebook_dm, pipeline_stage=captured, external_id=message_mid",
            "Lead Ads native form: parses lead_id, form_id, field_data array into LeadRecord fields",
            "Lead Ads Instant Experience: same parser as native form (identical payload structure)",
            "Lead Ads Messenger: parses form_data + preserves conversation_thread_id as metadata",
            "All 3 Lead Ads surfaces normalise to: source=facebook_lead_ads, pipeline_stage=captured, external_id=lead_id",
            "Facebook page access token stored AES-256-GCM encrypted in DB; refreshed on page_token_invalid error",
            "Deduplication: lead_id from Lead Ads is idempotency key — duplicate lead_id skipped",
            "All raw payloads stored in intake_event_log before processing",
            "Lead Ads leads skip Message Parser (explicit form submission — no classification needed)",
            "Unit tests: each of the 3 Lead Ads surfaces with sample payloads",
        ]
    ),
    epic_link=E3, sprint="Sprint 3", assignee="Dev B", priority="High",
    story_points=10, labels="ingestion,facebook,lead-ads,sprint3", components="Ingestion")

s3_email_csv = add("Story",
    "Implement email inbound parsing and Google Sheets/CSV bulk upload with LLM field mapping",
    ac(
        "Email inbound and bulk upload channels. CSV/Sheets field mapping uses an LLM call (Haiku) "
        "to map arbitrary column names to canonical LeadRecord fields. Bulk upload is async with job status tracking.",
        [
            "Email inbound: configured via SES/SendGrid inbound webhook OR IMAP polling (per tenant config)",
            "Email parser: extracts From address, Subject, Body; creates LeadRecord source=email, pipeline_stage=captured",
            "CSV upload: POST /leads/bulk/csv accepts multipart/form-data; max 1000 rows per batch",
            "Google Sheets import: POST /leads/bulk/sheets accepts {sheet_url}; uses service account OAuth to read",
            "LLM field mapping: sends first row + column headers to claude-haiku-4-5-20251001; receives {column: canonical_field} mapping",
            "Mapping confidence returned per column; low-confidence (<0.7) columns flagged in response for admin review",
            "Bulk upload is async: returns job_id immediately; GET /leads/bulk/jobs/{id} returns progress",
            "Bulk job: each row validated, mapped, and created as LeadRecord source=csv or source=sheets",
            "Failed rows recorded in job report with error per row (does not stop the rest of the batch)",
            "All bulk leads created with pipeline_stage=captured; skip Message Parser (structured data — no classification needed)",
        ]
    ),
    epic_link=E3, sprint="Sprint 3", assignee="Dev B", priority="Medium",
    story_points=8, labels="ingestion,email,csv,sheets,sprint3", components="Ingestion")

s3_message_parser = add("Story",
    "Implement Message Parser (claude-haiku-4-5-20251001): LEAD/NOISE/EXISTING_CUSTOMER/UNCLEAR routing",
    ac(
        "Build the Message Parser agent. DM messages only (WhatsApp, Instagram, Facebook DM). "
        "Classifies each message and routes to the correct pipeline stage. "
        "This is the first LLM gate in Pipeline 1 for the DM path.",
        [
            "Message Parser implemented as async LiteLLM call to claude-haiku-4-5-20251001",
            "Input: MessageParserInput {raw_message: str, channel: str, sender_metadata: dict, tenant_context: str}",
            "Output: MessageParserOutput {classification: Literal['LEAD','NOISE','EXISTING_CUSTOMER','UNCLEAR'], confidence: float, reason: str}",
            "LEAD routing: lead continues to enrichment stage (pipeline_stage=fetched)",
            "NOISE routing: pipeline_stage=insufficient_signal (terminal); no enrichment; no lead card created",
            "EXISTING_CUSTOMER routing: pipeline_stage=existing_customer (terminal); CRM sync event emitted; no scoring; no lead card created",
            "UNCLEAR routing: pipeline_stage=awaiting_clarification; salesperson notified to send clarifying message; waitForEvent registered with 24h timeout; lead exempt from score decay while paused",
            "On 24h timeout with no response: pipeline_stage transitions to insufficient_signal",
            "Message Parser is ONLY invoked for DM path (WhatsApp, Instagram, Facebook DM); Lead Ads and CSV/email skip parser",
            "Prompt stored in prompt_registry: name='message_parser', version='v1.0.0', is_active=True",
            "Parser result logged to intake_event_log: {classification, confidence, reason}",
            "Unit tests: 5 LEAD examples, 5 NOISE examples, 3 EXISTING_CUSTOMER examples, 3 UNCLEAR examples",
        ]
    ),
    epic_link=E3, sprint="Sprint 3", assignee="Dev C", priority="Highest",
    story_points=10, labels="llm,message-parser,routing,pipeline-1,sprint3", components="Ingestion,LLM,Orchestration")

s3_filter_dedup = add("Story",
    "Implement rule filter, deduplication, pre-flight validation, and Pydantic inbound schema enforcement",
    ac(
        "Build the pre-processing layer that runs before Message Parser. "
        "Rule filter removes known bot traffic and test messages. "
        "Deduplication prevents double-processing. Pre-flight validation ensures minimum fields exist.",
        [
            "Rule filter: per-tenant blocklist stored in tenant_config JSONB under 'filter_rules'",
            "Filter rule types: phone_prefix_blocklist, email_domain_blocklist, keyword_blocklist (in message body)",
            "Filtered leads: pipeline_stage=insufficient_signal, reason=rule_filter_match; logged to intake_event_log",
            "Deduplication key: (tenant_id, channel, external_id) — unique constraint in DB",
            "Duplicate: silently skipped; processing_status='duplicate_skipped' in intake_event_log",
            "Pre-flight validation — DM leads: phone or email required",
            "Pre-flight validation — Lead Ads: at least one of (name, company, email, phone) required",
            "Pre-flight failure: pipeline_stage=failed, reason=pre_flight_validation_failed",
            "Pydantic InboundMessage model validates all channel payloads; validation error → 422 with details logged",
            "All validation failures logged with correlation_id for debugging",
            "Unit tests: rule filter match, dedup skip, pre-flight failure for each channel type",
        ]
    ),
    epic_link=E3, sprint="Sprint 3", assignee="Dev C", priority="High",
    story_points=8, labels="ingestion,validation,deduplication,sprint3", components="Ingestion")

# ═══════════════════════════════════════════════════════════════
# SPRINT 4 — LEAD SCORING (Epic 4)
# Dev A: Enrichment service   |   Dev B: Signal extractors + disqual + Rating Agent   |   Dev C: Output Schema + lineage + decay
# ═══════════════════════════════════════════════════════════════

s4_enrichment = add("Story",
    "Implement enrichment service: all 9 providers, consent gate, quota tracking, AES-256-GCM PII encryption",
    ac(
        "Build the enrichment service. Calls 9 providers in parallel. Consent gate applied before enrichment. "
        "Enrichment quota tracked per tenant per provider per day. "
        "All PII fields encrypted with AES-256-GCM before any DB write.",
        [
            "Enrichment clients implemented for: Truecaller, Apollo.io, Surepass, Probe42, Tracxn, NewsCatcherAPI, IndiaMART/JustDial, Serper.dev, Google Places",
            "All 9 providers called concurrently via asyncio.gather; per-provider timeout=5s",
            "Provider failure: logged with reason; enrichment continues with remaining providers (partial enrichment is valid)",
            "Consent gate: DM leads require consent_flag=True before enrichment; Lead Ads skip gate (explicit form submission = implicit consent)",
            "Enrichment results merged into EnrichedLeadRecord using field priority order (documented per field type)",
            "enrichment_quota table tracking: (tenant_id, provider, date, count, daily_limit)",
            "Quota exceeded: provider skipped for that lead; logged with reason=quota_exceeded",
            "PII fields encrypted before DB write: phone, email, name, address using AES-256-GCM",
            "AES-256-GCM key stored in AWS Secrets Manager /lead-engine/encryption/pii-key; loaded at startup",
            "AES key never logged; key ID logged for audit purposes",
            "pipeline_stage transitions to enriched on successful enrichment service completion",
            "Unit tests: provider timeout handling, partial enrichment, quota exceeded, consent gate rejection",
        ]
    ),
    epic_link=E4, sprint="Sprint 4", assignee="Dev A", priority="Highest",
    story_points=13, labels="enrichment,pii,encryption,pipeline-1,sprint4", components="Enrichment")

s4_signals = add("Story",
    "Implement all 13 signal extractors and normalisation stage with ICPProfile weight application",
    ac(
        "Build the signal extraction layer. 13 pure-function extractors, each deterministic. "
        "Normalisation maps raw values to [0, 1]. ICPProfile weights applied to produce weighted_score. "
        "See [[analyses/signal-detection-rule-spec]] for named extractor definitions.",
        [
            "13 signal extractor functions implemented: intent, urgency, authority, budget, timeline, engagement, recency, channel_fit, geographic_fit, company_size_fit, role_fit, industry_fit, behavioral",
            "Each extractor signature: (lead: EnrichedLeadRecord, tenant_ctx: dict) → (detected: bool, value: float, evidence: str)",
            "Each extractor is a pure function: same input always produces same output",
            "value is always in [0.0, 1.0]; validated at extractor boundary",
            "Normalisation function applied per signal type (linear or sigmoid normalisation as specified in signal-detection-rule-spec)",
            "ICPProfile signal_weights applied: weighted_score = sum(weight_i * value_i for active signals)",
            "signal_scores stored in LeadRecord JSONB: {signal_type: {detected, value, evidence, weight}} per signal",
            "weighted_total_score stored as float on LeadRecord",
            "pipeline_stage transitions to normalised on completion",
            "Unit tests per extractor: ≥5 test cases each (true positive, true negative, edge case, zero value, max value)",
            "All 13 extractors covered by tests before story marked done",
        ]
    ),
    epic_link=E4, sprint="Sprint 4", assignee="Dev B", priority="Highest",
    story_points=13, labels="scoring,signals,normalisation,pipeline-1,sprint4", components="Scoring")

s4_rating_agent = add("Story",
    "Implement disqualification gate (DisqualRule stacking) and Rating Agent via claude-sonnet-4-6 with I/O schema v1.1.0",
    ac(
        "Build the disqualification gate using per-tenant DisqualRule[] config, then the Rating Agent LLM call. "
        "Stacking order (LOCKED): force_zero > score_cap > score_delta; result clamped to 0. "
        "INPUT/OUTPUT schema v1.1.0 validated with Pydantic before and after LLM call.",
        [
            "Disqualification gate reads DisqualRule[] from tenant_config",
            "DisqualRule TypedDict validated: condition_type (Literal), effect (Literal: score_cap|score_delta|force_zero), value (int), reason_label (str)",
            "Stacking order enforced: force_zero applied first → score capped if score_cap rule matches → score_delta applied last",
            "Final score clamped to 0 (cannot go negative)",
            "Disqualification reasons stored in disqual_adjustments JSONB on LeadRecord",
            "Rating Agent: async LiteLLM call to claude-sonnet-4-6",
            "INPUT schema v1.1.0 (Pydantic): {lead_id, enriched_fields, signal_scores, weighted_total_score, disqual_adjustments, tenant_persona_context, icp_profile_summary}",
            "INPUT validated before LLM call; invalid input → pipeline_stage=failed with reason=input_schema_invalid",
            "OUTPUT schema v1.1.0 (Pydantic): {raw_score: int [0-100], confidence: float [0.0-1.0], reasoning: str, flags: list[str]}",
            "OUTPUT validated after LLM call; invalid output triggers 1 retry then pipeline_stage=failed",
            "LLM call logged to task_execution: {agent='rating_agent', tokens_in, tokens_out, latency_ms, raw_score, success}",
            "Per-tenant concurrency cap enforced via LiteLLM proxy (default 5; reads tenant_config.concurrency_cap)",
        ]
    ),
    epic_link=E4, sprint="Sprint 4", assignee="Dev B", priority="Highest",
    story_points=13, labels="scoring,disqualification,rating-agent,llm,pipeline-1,sprint4", components="Scoring,LLM")

s4_output_schema = add("Story",
    "Implement Output Schema Layer: banding enforcement, completeness gate (threshold 0.60), schema coercion",
    ac(
        "Build the deterministic Output Schema Layer that wraps Rating Agent output. "
        "Zero LLM calls — fully deterministic. Threshold LOCKED at 0.60. "
        "Banding: HOT ≥ 80, WARM 50–79, COLD < 50.",
        [
            "Output Schema Layer implemented as a pure Python module (no LLM calls, no external calls)",
            "Banding enforcement: score ≥ 80 → bucket=HOT; 50 ≤ score < 80 → bucket=WARM; score < 50 → bucket=COLD",
            "Completeness gate: lead_completeness = non_null_required_fields / total_required_fields",
            "Required fields list: phone, email, name, company, source, channel, raw_message (DM) or form_fields (Lead Ads)",
            "lead_completeness < 0.60 → needs_review=True (threshold LOCKED — team decision 2026-05-22)",
            "Schema coercion: raw_score coerced to int(0-100); confidence coerced to float; missing optional flags defaulted to []",
            "Final output: LeadScore {score: int, bucket: HOT|WARM|COLD, confidence: float, needs_review: bool, lead_completeness: float, flags: list[str], reasoning: str}",
            "LeadScore stored to lead_score table; pipeline_stage transitions to scored",
            "needs_review=True leads: additionally queued for human_review workflow in Epic 5",
            "Unit tests: HOT/WARM/COLD boundaries (79/80, 49/50), completeness at 0.59 and 0.61, coercion edge cases, needs_review flag",
        ]
    ),
    epic_link=E4, sprint="Sprint 4", assignee="Dev C", priority="Highest",
    story_points=10, labels="scoring,output-schema,banding,pipeline-1,sprint4", components="Scoring")

s4_lineage = add("Story",
    "Implement lineage write order, dead letter mechanism, crash recovery, and pipeline_stage audit trail",
    ac(
        "Implement the lineage audit trail with the LOCKED write order: "
        "lineage_record → task_execution → pipeline_run → pipeline_stage (always last). "
        "Dead letter on write failure. Crash recovery resumes from last successful stage. "
        "5-year retention on audit tables.",
        [
            "Lineage write order enforced in all scoring pipeline stages: lineage_record first, then task_execution, then pipeline_run, then pipeline_stage last",
            "pipeline_stage table is append-only: each transition writes a NEW row (never UPDATE)",
            "pipeline_stage columns: (lead_id, stage, entered_at, exited_at, duration_ms, error_details)",
            "Write failure: does NOT raise to primary API; escalated via dead letter mechanism",
            "Dead letter: 3 retries at 30s / 5m / 30m intervals using exponential backoff",
            "On retry exhaustion: insert to failed_audit_log + emit CRITICAL CloudWatch metric (name: LineageWriteExhausted) + send admin alert email",
            "5-year retention: lineage_record, pipeline_stage, failed_audit_log tables have PostgreSQL table-level retention annotation",
            "Crash recovery: on scoring service restart, query pipeline_stage for leads in non-terminal stages; re-enqueue in workflow engine at last completed stage",
            "Crash recovery is idempotent: re-processing an already-completed stage is detected and skipped",
            "Integration test: simulate write failure; verify dead letter retries fire; verify CRITICAL metric emitted on exhaustion",
        ]
    ),
    epic_link=E4, sprint="Sprint 4", assignee="Dev C", priority="High",
    story_points=8, labels="lineage,audit,crash-recovery,dead-letter,pipeline-1,sprint4", components="Scoring,Infrastructure")

s4_score_decay = add("Story",
    "Implement score decay background job, SLA timers, and awaiting_clarification exemption",
    ac(
        "Implement score decay per LOCKED mechanics: −10 at 7 days, −20 at 14 days, force COLD at 30 days. "
        "Delta adjustment only (no full rescore). SLA restarts only on bucket upgrade. "
        "awaiting_clarification leads exempt while paused. See [[concepts/score-decay]].",
        [
            "Score decay job: scheduled cron task, runs daily at 00:00 UTC",
            "Query: all scored leads where last_scored_at < now() - interval AND pipeline_stage='scored' AND bucket != 'COLD'",
            "Day 7 decay: new_score = max(0, current_score - 10); bucket recomputed",
            "Day 14 decay: new_score = max(0, current_score - 20) from original score (not stacked −30); bucket recomputed",
            "Day 30 decay: bucket forced to COLD regardless of score",
            "Delta adjustment only — no new Rating Agent call; existing signal_scores unchanged",
            "New lineage_record written per decay event with decay_reason: 'decay_7d' | 'decay_14d' | 'decay_30d'",
            "SLA timer: HOT leads must be actioned within 2h, WARM within 24h, COLD within 72h",
            "SLA clock restarts ONLY on bucket upgrade (COLD→WARM, WARM→HOT); restarts on score update that changes bucket",
            "awaiting_clarification leads: decay job skips these leads entirely while pipeline_stage='awaiting_clarification'",
            "HOT SLA breach (2h): emit CloudWatch metric SLABreachHOT + notify team_lead via notification service",
            "Unit tests: decay at day 7, 14, 30; bucket boundary changes; SLA restart on bucket upgrade; awaiting_clarification exemption",
        ]
    ),
    epic_link=E4, sprint="Sprint 4", assignee="Dev C", priority="High",
    story_points=8, labels="score-decay,sla,background-job,pipeline-1,sprint4", components="Scoring")

# ═══════════════════════════════════════════════════════════════
# SPRINT 5 — DELIVERY & SALESPERSON UI (Epic 5)
# Dev A: Real-time delivery + SLA alerts   |   Dev B: Human review UI + dashboards   |   Dev C: CRM sync + webhooks
# ═══════════════════════════════════════════════════════════════

s5_realtime_delivery = add("Story",
    "Implement real-time lead card delivery via Pusher/Soketi with HOT push notification",
    ac(
        "When pipeline_stage transitions to delivered, push lead card to salesperson's channel. "
        "HOT leads trigger additional push notification. Channel isolated per tenant. "
        "Uses real-time provider from Sprint 1 spike decision.",
        [
            "Lead card pushed on pipeline_stage=delivered via Pusher/Soketi channel",
            "Channel naming: tenant_{tenant_id}_leads (one channel per tenant)",
            "Lead card payload: {lead_id, name_masked, score, bucket, channel, summary, top_3_signals, needs_review, created_at, sla_deadline}",
            "HOT leads: additional push notification via notification service (in-app alert + email to assigned salesperson)",
            "Real-time channel auth: Clerk JWT verified before channel subscription (Pusher/Soketi auth endpoint)",
            "RBAC: only salesperson and team_lead roles can subscribe to tenant lead channel",
            "Delivery failure: retried 3 times (5s / 30s / 120s); on exhaustion: lead flagged delivered_failed + CRITICAL CloudWatch metric",
            "Delivery latency SLO: HOT lead delivered within 10 seconds of pipeline_stage=scored",
            "pipeline_stage transitions to delivered on successful push",
        ]
    ),
    epic_link=E5, sprint="Sprint 5", assignee="Dev A", priority="Highest",
    story_points=8, labels="delivery,realtime,notification,sprint5", components="Delivery")

s5_sla_alerts = add("Story",
    "Implement HOT SLA breach alerting, scheduled daily report generation and delivery",
    ac(
        "SLA breach detection for HOT leads (2h). Scheduled daily report emailed to admin "
        "with lead volume, conversion rate, and SLA compliance metrics.",
        [
            "HOT SLA breach detection: background job polls every 15 minutes for HOT leads where sla_deadline < now() and pipeline_stage=delivered",
            "HOT SLA breach: emit CloudWatch metric SLABreachHOT + notify team_lead (in-app + email)",
            "WARM SLA breach (24h): emit CloudWatch metric SLABreachWARM + log only (no direct notification)",
            "SLA breach event stored in sla_breach_log: {lead_id, bucket, breach_at, notified}",
            "Daily report: generated at 07:00 UTC (or tenant-configured timezone)",
            "Report content: total_leads, HOT/WARM/COLD counts, SLA_compliance_% (per bucket), avg_score, top_signal_types",
            "Report delivered via email to admin role users of each tenant",
            "Report generation is async; failure logged to CloudWatch but does not affect pipeline",
            "Report available via GET /reports/daily?date=YYYY-MM-DD for historical access",
        ]
    ),
    epic_link=E5, sprint="Sprint 5", assignee="Dev A", priority="Medium",
    story_points=5, labels="sla,alerts,reporting,sprint5", components="Delivery,Reporting")

s5_human_review = add("Story",
    "Build human review queue UI and awaiting-clarification notification with countdown timer",
    ac(
        "Salesperson-facing UI for human review queue. Leads with needs_review=True or awaiting_clarification "
        "state appear in the queue. awaiting_clarification shows 24h countdown. Role-scoped visibility.",
        [
            "Human review queue: GET /leads/review-queue returns needs_review=True leads sorted by score DESC",
            "Queue item fields: lead_id, name_masked, score, bucket, top_signals, needs_review_reason, awaiting_since, sla_deadline",
            "awaiting_clarification leads shown with countdown: time_remaining = 24h - (now - awaiting_since)",
            "Salesperson notification on awaiting_clarification: in-app notification + email with instructions to send clarifying message",
            "Action endpoints: POST /leads/{id}/actions/mark_contacted, /reject, /escalate_to_team_lead",
            "mark_contacted: sets pipeline_stage to human_review; records salesperson_id and contacted_at",
            "reject: sets pipeline_stage to failed, reason=salesperson_rejected; records rejection_reason",
            "escalate_to_team_lead: notifies team_lead; adds to team_lead queue",
            "On clarifying response received: lead exits awaiting_clarification; re-queues at fetched stage for re-scoring",
            "RBAC: salesperson sees own assigned leads; team_lead sees all tenant leads",
            "UI component: queue list with real-time updates via Pusher/Soketi subscription",
        ]
    ),
    epic_link=E5, sprint="Sprint 5", assignee="Dev B", priority="High",
    story_points=10, labels="ui,human-review,awaiting-clarification,sprint5", components="UI,Delivery")

s5_dashboards = add("Story",
    "Build role-scoped dashboards: salesperson pipeline view, team lead overview, admin metrics",
    ac(
        "Three dashboards, each scoped to the caller's role. Data served from reporting service API. "
        "Real-time updates for new HOT leads only; everything else polls every 60s.",
        [
            "Salesperson dashboard — GET /dashboard/salesperson: {my_leads_today, hot_count, sla_timers, pipeline_stage_breakdown, recent_leads: list}",
            "Team lead dashboard — GET /dashboard/team_lead: {team_leads: list, sla_compliance_%, conversion_rate, leads_awaiting_review, top_performers: list}",
            "Admin dashboard — GET /dashboard/admin: {total_leads, pipeline_throughput_per_hour, enrichment_quota_usage, llm_cost_estimate_usd, active_tenants}",
            "All dashboard endpoints enforce RBAC: wrong role → 403",
            "Dashboard data cached in reporting service with 60s TTL; real-time push only for new HOT lead events",
            "Reporting service reads from replica DB (if available) to avoid read load on primary",
            "LLM cost estimate: sum of task_execution.tokens_in + tokens_out × model pricing; updated daily",
            "All timestamps returned in ISO 8601 with UTC offset",
        ]
    ),
    epic_link=E5, sprint="Sprint 5", assignee="Dev B", priority="Medium",
    story_points=8, labels="ui,dashboard,reporting,sprint5", components="UI,Reporting")

s5_crm_sync = add("Story",
    "Implement CRM sync for Salesforce and HubSpot triggered on lead delivery and existing_customer routing",
    ac(
        "Async CRM sync on pipeline_stage=delivered and pipeline_stage=existing_customer. "
        "Supports Salesforce (Lead object) and HubSpot (Contact + Deal). Non-blocking. "
        "Retry on failure with dead letter on exhaustion.",
        [
            "CRM sync triggered async on: pipeline_stage=delivered AND pipeline_stage=existing_customer",
            "Salesforce sync: create Lead object with mapped fields (name, company, email, phone, score, bucket, lead_source)",
            "Salesforce Lead ID stored back on LeadRecord: crm_external_id",
            "HubSpot sync: create Contact + Deal; Contact email = lead email; Deal name = 'Lead from {channel} — {bucket}'",
            "HubSpot contact_id and deal_id stored on LeadRecord",
            "existing_customer sync: create/update Contact in CRM; flag existing=True; no Deal created",
            "CRM credentials (access token, instance URL) stored AES-256-GCM encrypted per tenant in Secrets Manager",
            "Tenant can disable CRM sync via tenant_config: crm_enabled=False",
            "Sync failure: retried 3 times (30s / 5m / 30m); on exhaustion: crm_sync_failed=True on lead + admin alert",
            "Sync result stored in crm_sync_record: {lead_id, crm_type, external_id, status, attempted_at, error}",
        ]
    ),
    epic_link=E5, sprint="Sprint 5", assignee="Dev C", priority="High",
    story_points=8, labels="crm,salesforce,hubspot,integration,sprint5", components="Delivery,Integration")

s5_outbound_webhooks = add("Story",
    "Implement outbound webhook system with HMAC-SHA256 signing, retry, and delivery log",
    ac(
        "Tenants can register webhook URLs to receive lead events. "
        "All outbound payloads signed with HMAC-SHA256. Async delivery with retry and delivery log.",
        [
            "POST /webhooks (admin role): registers {url, secret, event_types: list[str], is_active: bool}",
            "Supported event_types: lead_scored, lead_delivered, lead_updated, existing_customer, awaiting_clarification, sla_breach",
            "Outbound payload signed: X-Lead-Engine-Signature header = HMAC-SHA256(secret, payload_json)",
            "Delivery: async HTTP POST to registered URL; timeout=10s",
            "Non-2xx response: retried 3 times (30s / 5m / 30m)",
            "Delivery result logged in webhook_delivery_log: {webhook_id, event_type, attempt, status_code, delivered_at, error}",
            "POST /webhooks/{id}/test: sends synthetic payload for the registered event type",
            "GET /webhooks/{id}/deliveries: returns last 50 delivery records for debugging",
            "DELETE /webhooks/{id}: deactivates webhook (soft delete)",
            "Webhook secret never returned in API responses after creation (write-only)",
        ]
    ),
    epic_link=E5, sprint="Sprint 5", assignee="Dev C", priority="Medium",
    story_points=5, labels="webhooks,integration,delivery,sprint5", components="Delivery,Integration")

# ═══════════════════════════════════════════════════════════════
# SPRINT 6 — FEEDBACK LOOP (Epic 6)
# Dev A: Feedback API + pattern detection   |   Dev B: Quality metrics + admin CLI
# ═══════════════════════════════════════════════════════════════

s6_feedback_api = add("Story",
    "Implement feedback collection API and outcome attribution logic",
    ac(
        "Salespeople record lead outcomes. Attribution logic traces which signals and LLM reasoning "
        "contributed to the score. Feedback is the foundation for quality metrics (Sprint 6 Dev B) and "
        "pattern detection.",
        [
            "POST /feedback/{lead_id}: {outcome: converted|rejected|contacted|no_show, deal_value?: float, rejection_reason?: str, notes?: str}",
            "Salesperson and team_lead roles can submit feedback",
            "Feedback stored in feedback_record: {lead_id, outcome, deal_value, rejection_reason, notes, submitted_by, submitted_at}",
            "Attribution logic: reads signal_scores, disqual_adjustments, and rating_agent task_execution for the lead",
            "Attribution output: {top_contributing_signals: list[{signal_type, value, evidence}], rating_confidence: float, was_disqualified: bool, disqual_reasons: list}",
            "Attribution stored in feedback_record.attribution JSONB column",
            "Multiple feedback events per lead are allowed (e.g., first contact, then conversion)",
            "GET /feedback/{lead_id}: returns all feedback events for the lead (team_lead or admin role)",
            "Feedback events trigger quality metrics recalculation job (async, non-blocking)",
        ]
    ),
    epic_link=E6, sprint="Sprint 6", assignee="Dev A", priority="High",
    story_points=8, labels="feedback,attribution,sprint6", components="Feedback")

s6_pattern_detection = add("Story",
    "Implement feedback pattern detection and team lead recommendation surface",
    ac(
        "Analyse feedback patterns to detect systematic scoring issues. "
        "Surface actionable recommendations to team leads. Runs weekly.",
        [
            "Pattern detection job: runs weekly (Monday 02:00 UTC); analyses last 30 days of feedback_record",
            "False positive detection: signal X contributes significantly to HOT score AND lead outcome=rejected in >40% of HOT leads → flag signal X",
            "False negative detection: leads scored COLD (score < 50) AND outcome=converted in >20% of COLD leads → flag scoring calibration issue",
            "Recommendation types: 'reduce_signal_weight', 'review_icp_criteria', 'update_rating_agent_prompt', 'review_disqual_rules'",
            "Recommendations stored: {tenant_id, signal_type, issue_type, frequency, sample_lead_ids, recommendation_text, created_at, status: active|dismissed}",
            "GET /recommendations (team_lead or admin role): returns active recommendations sorted by frequency DESC",
            "POST /recommendations/{id}/dismiss: admin or team_lead can dismiss; stores dismissal reason",
            "Minimum data threshold: pattern detection requires ≥20 feedback records in the period (skips if fewer)",
        ]
    ),
    epic_link=E6, sprint="Sprint 6", assignee="Dev A", priority="Medium",
    story_points=5, labels="feedback,pattern-detection,sprint6", components="Feedback")

s6_quality_metrics = add("Story",
    "Implement quality snapshots: AP/C/AR metrics and daily_enrichment_health_snapshot",
    ac(
        "Quality metrics system. AP (Average Precision), C (Conversion rate), AR (Acceptance Rate) "
        "computed from feedback data. daily_enrichment_health_snapshot for enrichment provider health.",
        [
            "daily_enrichment_health_snapshot job: runs daily at 01:00 UTC",
            "Snapshot per provider: {provider, date, availability_%: float, avg_fields_populated: int, avg_latency_ms: float, error_rate_%: float}",
            "Snapshots stored in enrichment_health_snapshot table",
            "AP metric (Average Precision): precision@1 = fraction of HOT leads converted; precision@3 = fraction of top-3-scored leads converted",
            "C metric (Conversion rate): leads_converted / leads_delivered per bucket (HOT, WARM, COLD) per tenant per week",
            "AR metric (Acceptance Rate): leads_actioned / leads_delivered per tenant per week (action = contacted or converted)",
            "Metrics stored in quality_metrics: {tenant_id, metric_type, metric_subtype, value, period_start, period_end, computed_at}",
            "GET /quality/metrics?tenant_id=X&metric=AP&period=7d: returns metric timeseries",
            "GET /quality/enrichment/health?provider=X&period=30d: returns health snapshot timeseries",
            "Minimum data: metrics require ≥10 feedback records in period (returns null_insufficient_data if fewer)",
        ]
    ),
    epic_link=E6, sprint="Sprint 6", assignee="Dev B", priority="Medium",
    story_points=8, labels="quality,metrics,enrichment,sprint6", components="Feedback,Reporting")

s6_admin_cli = add("Story",
    "Implement admin CLI suite (5 commands) for operational management",
    ac(
        "Python Click CLI tool `lead-engine` with 5 operational commands. "
        "All commands authenticate via API key (admin role). All support --dry-run.",
        [
            "CLI package installable: `pip install lead-engine-cli`",
            "Command 1: `lead-engine leads reprocess <lead_id> [--dry-run]` — requeue lead at captured stage",
            "Command 2: `lead-engine tenant suspend <tenant_id> [--reason TEXT] [--dry-run]` — suspend tenant; queue drain stops",
            "Command 3: `lead-engine tenant activate <tenant_id> [--dry-run]` — activate tenant; queue drain starts",
            "Command 4: `lead-engine prompts promote <name> <version> [--dry-run]` — promote prompt version (evaluations must pass first)",
            "Command 5: `lead-engine quality report <tenant_id> --period 7d` — print quality metrics table to stdout",
            "All commands: read LEAD_ENGINE_API_KEY from env var; fail if missing",
            "All commands: --dry-run prints what would be done without making any changes",
            "All commands log to admin_cli_log: {command, args, user_api_key_id, dry_run, result, executed_at}",
            "Unit tests for all 5 commands with --dry-run flag",
        ]
    ),
    epic_link=E6, sprint="Sprint 6", assignee="Dev B", priority="Medium",
    story_points=5, labels="admin,cli,tooling,sprint6", components="Feedback")

# ═══════════════════════════════════════════════════════════════
# SPRINT 6 — SECURITY HARDENING (Epic 7)
# Dev C: PII audit + RBAC adversarial + session hardening (all security hardening owned by Dev C)
# ═══════════════════════════════════════════════════════════════

s7_pii_audit = add("Story",
    "PII field audit: verify AES-256-GCM on all PII columns, produce data map, test round-trip",
    ac(
        "Audit all 33 DB tables for PII. Verify AES-256-GCM encryption on all PII columns. "
        "Produce authoritative PII data map. Fix any gaps found.",
        [
            "PII field enumeration: review all 33 tables; identify all PII columns (phone, email, name, address, company, social handles, message content)",
            "Treatment classification per column: encrypted (AES-256-GCM) | hashed (SHA-256, one-way) | plain (no PII) | not-applicable",
            "PII data map document written: wiki/analyses/pii-data-map.md — table → column → treatment",
            "Any unencrypted PII columns found: Alembic migration written to encrypt; data backfilled",
            "AES key rotation procedure documented: key rotation steps, zero-downtime rotation approach",
            "Round-trip tests: encrypt(plaintext) → store → retrieve → decrypt → assert equals plaintext for each PII field type",
            "Negative test: attempt to read raw PII from DB without decryption key → assert ciphertext returned",
            "CloudWatch alarm added: if AES key fetch fails at startup → CRITICAL alert (no service should run without key)",
        ]
    ),
    epic_link=E7, sprint="Sprint 6", assignee="Dev C", priority="High",
    story_points=8, labels="security,pii,encryption,audit,sprint6", components="Security")

s7_rbac_adversarial = add("Story",
    "RBAC enforcement audit and cross-tenant RLS adversarial test suite",
    ac(
        "Audit every API endpoint for RBAC decorator presence. "
        "Run adversarial RLS tests across 3 tenants with real JWTs. All adversarial tests must be automated.",
        [
            "Endpoint audit: enumerate all HTTP routes across all 8 services; confirm RBAC decorator is present and correct on each",
            "Any endpoint missing RBAC: add decorator or document why it's public (e.g., POST /webhooks/meta must be public)",
            "Adversarial test 1: JWT for tenant A; GET /leads → assert 0 rows from tenant B; assert all rows have tenant_id=A",
            "Adversarial test 2: JWT for tenant A; POST /leads (body with tenant_id=B) → assert RLS violation or 403",
            "Adversarial test 3: JWT for tenant A; GET /tenants/B/config → assert 403 or 0 rows",
            "Adversarial test 4: admin JWT without tenant_id claim → assert 403 on all tenant-scoped endpoints",
            "Adversarial test 5: expired JWT → assert 401 token_expired on all endpoints",
            "Adversarial test 6: viewer role attempting POST /leads → assert 403",
            "All 6 adversarial tests added to automated pytest suite (not manual)",
            "Findings report produced: wiki/analyses/security-adversarial-results.md",
        ]
    ),
    epic_link=E7, sprint="Sprint 6", assignee="Dev C", priority="High",
    story_points=8, labels="security,rbac,rls,adversarial,sprint6", components="Security")

s7_session_hardening = add("Story",
    "Implement webhook replay protection (5-min window) and session hardening",
    ac(
        "Timestamp-based replay protection on ALL inbound webhooks. "
        "Session hardening: short JWT expiry, secure cookie flags, HTTPS enforcement, CORS lockdown.",
        [
            "Inbound webhook replay protection: timestamp extracted from payload or X-Timestamp header",
            "Replay protection rule: abs(server_time - webhook_time) > 300 seconds → 403 Forbidden with error: replay_rejected",
            "Replay protection applied to: POST /webhooks/meta, POST /webhooks/crm/callback, all other inbound webhook routes",
            "Clerk session configuration: access token expiry ≤ 15 minutes; refresh token expiry ≤ 7 days",
            "Secure cookie flags: HttpOnly=True, Secure=True, SameSite=Strict on all session cookies",
            "HTTPS enforcement: HTTP requests redirected 301 to HTTPS on all services",
            "CORS: allowedOrigins configured to only permitted frontend domains (no wildcard *)",
            "Content Security Policy headers added to all API responses",
            "REDACTED log scan: grep all CloudWatch log groups for patterns matching email addresses or phone numbers; assert 0 matches",
            "Unit tests: replay protection at 299s (accept), 301s (reject), 0s (accept)",
        ]
    ),
    epic_link=E7, sprint="Sprint 6", assignee="Dev C", priority="High",
    story_points=5, labels="security,webhook,session,cors,sprint6", components="Security")

# ═══════════════════════════════════════════════════════════════
# SPRINT 7 — OBSERVABILITY & CI/CD (Epic 8)
# Dev A: CloudWatch + runbook + autoscaling   |   Dev B: CI/CD + backups + correlation audit
# ═══════════════════════════════════════════════════════════════

s8_cloudwatch = add("Story",
    "Build CloudWatch dashboards, configure alert thresholds, and enable autoscaling for 3 services",
    ac(
        "CloudWatch dashboards for all 8 services. Alert thresholds for error rate and latency. "
        "Autoscaling for Ingestion, Scoring Agent, and Orchestration services.",
        [
            "CloudWatch dashboard per service (8 dashboards): request_rate, error_rate_%, p50/p95/p99 latency, memory_utilization, cpu_utilization",
            "Composite alarm: error_rate > 1% for 2 consecutive minutes → WARNING",
            "Composite alarm: error_rate > 5% for 2 consecutive minutes → CRITICAL + PagerDuty/email alert",
            "Latency alarm: p99 > 5000ms for any service → WARNING",
            "Autoscaling configured for: ingestion-service, scoring-service, orchestration-service",
            "Scale-out: CPU > 70% for 2 consecutive minutes → add 1 task",
            "Scale-in: CPU < 30% for 10 consecutive minutes → remove 1 task",
            "Min tasks per service: 1; Max tasks: 10",
            "LineageWriteExhausted metric alarm: any occurrence → CRITICAL immediate alert",
            "SLABreachHOT metric alarm: count > 5 in 1h → WARNING alert to team_lead",
            "All alarms routed to SNS topic → email + optionally PagerDuty",
        ]
    ),
    epic_link=E8, sprint="Sprint 7", assignee="Dev A", priority="High",
    story_points=8, labels="observability,cloudwatch,autoscaling,sprint7", components="Observability,Infrastructure")

s8_runbook = add("Story",
    "Write operational runbook for all CRITICAL alert scenarios",
    ac(
        "Runbook document covering every CRITICAL CloudWatch alert. "
        "Linked from each alarm description. Stored in wiki.",
        [
            "Runbook document written at wiki/analyses/operational-runbook.md",
            "Scenario 1: dead letter exhaustion (LineageWriteExhausted) → check failed_audit_log, verify DB connectivity, restart dead letter processor",
            "Scenario 2: scoring service CRITICAL error rate → check ECS task health, check LiteLLM proxy, roll back last deploy if recent",
            "Scenario 3: enrichment provider failure (all providers failing) → check quota status, verify API keys in Secrets Manager, activate fallback",
            "Scenario 4: HOT SLA breach rate > 5 in 1h → check scoring throughput, check concurrency cap config, check delivery service",
            "Scenario 5: RLS violation alert → freeze affected tenant access, audit cross-tenant query logs, escalate to security",
            "Each scenario includes: detection signal, immediate mitigation steps, root cause investigation steps, escalation path",
            "Runbook linked from all CRITICAL CloudWatch alarm descriptions",
            "Runbook reviewed by all 3 developers; sign-off recorded",
        ]
    ),
    epic_link=E8, sprint="Sprint 7", assignee="Dev A", priority="Medium",
    story_points=3, labels="observability,runbook,documentation,sprint7", components="Observability")

s8_cicd = add("Story",
    "Build staging CI/CD pipeline with production promotion gates and automated Docker image management",
    ac(
        "Staging auto-deploys on merge to main. Production requires manual approval + smoke tests passing. "
        "Docker images tagged with git SHA. Rollback via previous ECR image.",
        [
            "Staging pipeline: merge to main → build Docker images (tagged with git SHA) → push to ECR → ECS rolling update → health check gate",
            "All 8 service images built and pushed to individual ECR repositories",
            "ECS rolling update: new task launched, health check must pass before old task terminated",
            "Staging smoke tests: GET /health on all 8 services returns 200 after deploy",
            "Production pipeline: requires manual approval in GitHub Actions environment (named 'production')",
            "Production gate: all unit tests green AND staging smoke tests pass AND manual approver confirmed",
            "Production deploy: same ECS rolling update pattern as staging",
            "Rollback command: `lead-engine deploy rollback --env prod --service <name>` re-deploys previous ECR image",
            "Deploy notification: GitHub Actions sends status update (Slack channel or email) on deploy start / success / failure",
            "Image retention policy: ECR keeps last 10 images per service; older images automatically pruned",
        ]
    ),
    epic_link=E8, sprint="Sprint 7", assignee="Dev B", priority="High",
    story_points=10, labels="ci-cd,devops,deployment,sprint7", components="DevOps")

s8_backups = add("Story",
    "Implement automated PostgreSQL backups (PITR) and audit correlation_id propagation across all services",
    ac(
        "Automated daily DB backups with point-in-time recovery. "
        "Correlation_id propagation audited across all 8 services end-to-end.",
        [
            "Automated backup: daily full PostgreSQL backup to S3 at 02:00 UTC",
            "WAL archiving: continuous WAL shipping to S3 for point-in-time recovery",
            "Backup retention: 30 days",
            "PITR test: restore DB to a point 12h in the past; verify data integrity; document steps",
            "Backup success CloudWatch metric: BackupSuccess=1 per day; alarm if BackupSuccess=0 for 2 consecutive days",
            "Correlation_id propagation audit: trace a synthetic lead through all 8 services; verify X-Correlation-ID present in every inter-service HTTP call",
            "Log audit: verify correlation_id field appears in every log line for the traced lead across all services",
            "Gaps found: fix X-Correlation-ID header propagation and re-audit",
            "Audit report written: wiki/analyses/correlation-id-audit.md listing all service-to-service calls and propagation status",
        ]
    ),
    epic_link=E8, sprint="Sprint 7", assignee="Dev B", priority="Medium",
    story_points=5, labels="database,backup,observability,correlation-id,sprint7", components="Infrastructure,Observability")

# ═══════════════════════════════════════════════════════════════
# SPRINT 7 — TESTING & VALIDATION (Epic 9)
# Dev C: all E2E golden paths + LLM eval + Govmen onboarding
# ═══════════════════════════════════════════════════════════════

s9_e2e_hot = add("Story",
    "E2E Golden Path 1: HOT B2B lead via WhatsApp → delivered (Gamoft tenant)",
    ac(
        "Full end-to-end test: synthetic WhatsApp DM → Message Parser LEAD → enrichment → signals → HOT score → "
        "real-time delivery → salesperson queue. All lineage writes verified. "
        "Uses Gamoft B2B tenant with configured persona/ICP/signal profile.",
        [
            "Gamoft B2B tenant fully configured: persona, ICP, signal config all set via Pipeline 2",
            "Synthetic WhatsApp DM submitted via POST /webhooks/meta with valid HMAC-SHA256 signature",
            "Webhook returns 200 within 200ms",
            "Message Parser classifies as LEAD with confidence ≥ 0.80",
            "Enrichment: at least 3 of 9 providers return non-empty data",
            "Signal extraction: at least 5 of 13 signals detected (detected=True)",
            "Disqualification gate: no disqualification rules triggered (or explicitly tested with a rule)",
            "Rating Agent call succeeds: raw_score ≥ 80",
            "Output Schema Layer: bucket=HOT, needs_review=False (lead_completeness ≥ 0.60)",
            "Lead card delivered via Pusher/Soketi within 10 seconds of pipeline_stage=scored",
            "HOT push notification sent to assigned salesperson",
            "Lineage audit: confirm lineage_record → task_execution → pipeline_run → pipeline_stage write order in DB",
            "pipeline_stage sequence verified: captured→fetched→enriched→normalised→scored→delivered",
            "E2E total latency (DM received → delivered) logged; assert < 60 seconds",
        ]
    ),
    epic_link=E9, sprint="Sprint 7", assignee="Dev C", priority="Highest",
    story_points=8, labels="e2e,testing,golden-path,hot,b2b,sprint7", components="QA")

s9_e2e_cold = add("Story",
    "E2E Golden Path 2: COLD SMB lead via Facebook Lead Ads → needs_review queue (Urvee Organics tenant)",
    ac(
        "Full end-to-end test for COLD/needs_review scenario. Facebook Lead Ads form submission with sparse data. "
        "lead_completeness < 0.60 → needs_review=True. Score decay verified.",
        [
            "Urvee Organics B2C tenant fully configured with Pipeline 2",
            "Synthetic Facebook Lead Ads payload submitted with minimal fields (name + email only; no phone, company)",
            "Message Parser NOT invoked (Lead Ads path skips parser) — verified by checking no parser task_execution created",
            "Enrichment: simulate sparse result — max 1 provider returns data; rest return empty",
            "lead_completeness calculated: assert < 0.60",
            "Rating Agent returns raw_score < 50 (COLD)",
            "Output Schema Layer: bucket=COLD, needs_review=True",
            "Lead appears in human review queue within 30 seconds",
            "COLD SLA timer started (72h deadline set)",
            "Score decay simulation: mock system time to +7 days; re-run decay job; assert score reduced by 10 and new lineage_record written with decay_reason='decay_7d'",
            "pipeline_stage sequence verified: captured→fetched→enriched→normalised→scored→delivered",
        ]
    ),
    epic_link=E9, sprint="Sprint 7", assignee="Dev C", priority="High",
    story_points=8, labels="e2e,testing,golden-path,cold,b2c,sprint7", components="QA")

s9_e2e_noise = add("Story",
    "E2E Golden Path 3: NOISE message → insufficient_signal terminal + EXISTING_CUSTOMER routing validation",
    ac(
        "E2E test for NOISE routing (no lead created). Also validates EXISTING_CUSTOMER routing "
        "independently (CRM sync emitted, no lead card created).",
        [
            "Synthetic spam WhatsApp DM submitted: message = 'test test 123 abc'",
            "Message Parser classifies as NOISE with confidence ≥ 0.80",
            "pipeline_stage set to insufficient_signal (terminal) immediately",
            "Assertions: no EnrichedLeadRecord created; no signal_scores computed; no Rating Agent called; no lead card delivered",
            "intake_event_log record shows classification=NOISE with reason",
            "EXISTING_CUSTOMER routing test (separate synthetic DM): message contains clear existing customer signal",
            "Message Parser classifies as EXISTING_CUSTOMER",
            "pipeline_stage set to existing_customer (terminal)",
            "CRM sync event emitted (verify crm_sync_record created)",
            "Assertions: no scoring performed; no lead card created; no delivery push",
            "Both terminal state tests verify the pipeline_stage row is the final row for the lead (no further transitions)",
        ]
    ),
    epic_link=E9, sprint="Sprint 7", assignee="Dev C", priority="High",
    story_points=5, labels="e2e,testing,golden-path,noise,routing,sprint7", components="QA")

s9_llm_eval = add("Story",
    "LLM evaluation suite: 20 test cases per agent, schema validity gate, full test coverage audit",
    ac(
        "Evaluation suite for all 5 LLM agents. Runs in CI on prompt version changes. "
        "Full test coverage audit across all 8 services with coverage report.",
        [
            "20 test cases per agent: Persona Agent, ICP Agent, Signal Agent, Rating Agent, Message Parser (100 total)",
            "Each test case: {input, expected_output_schema_valid: bool, expected_classification?: str, expected_score_range?: tuple}",
            "Eval metrics per agent: schema_validity_rate (% outputs passing Pydantic validation), no_pii_leakage_rate, classification_accuracy (Message Parser only)",
            "Promotion gate: schema_validity_rate ≥ 90% required before prompt_registry promotion is allowed",
            "Eval suite integrated into CI: runs on any PR that modifies files under prompt_registry/",
            "pytest --cov run across all 8 services: produces coverage.xml",
            "Coverage report: line coverage per service, function coverage per service",
            "Target: ≥80% line coverage on scoring-service and ingestion-service",
            "Coverage gaps identified: critical gaps (scoring logic, disqual gate, banding) must be fixed before story marked done",
            "Coverage report committed to docs/coverage-report.md",
        ]
    ),
    epic_link=E9, sprint="Sprint 7", assignee="Dev C", priority="High",
    story_points=8, labels="testing,llm-eval,coverage,sprint7", components="QA")

s9_govmen = add("Story",
    "Govmen tenant onboarding: Pipeline 2 run and synthetic lead E2E validation",
    ac(
        "Onboard the Govmen (government/public sector) tenant through Pipeline 2. "
        "Validate agent outputs for a novel vertical. Process at least one synthetic lead through Pipeline 1.",
        [
            "Govmen tenant created via POST /tenants with business_type=government",
            "Tenant config specified: target_market=public_sector, example_customers=[list of example government contacts]",
            "Pipeline 2 run: Persona Agent, ICP Agent, Signal Agent all complete successfully",
            "PersonaObject, ICPProfile, SignalConfig stored in Govmen tenant_config JSONB",
            "Pipeline 2 output manually reviewed by team: persona and ICP reviewed for accuracy in government/procurement context",
            "Any vertical-specific signal issues documented (e.g., urgency signals may behave differently for government procurement cycles)",
            "At least 1 synthetic lead submitted via CSV upload and processed through full Pipeline 1",
            "Lead score reviewed for reasonableness given Govmen vertical context",
            "Findings and any vertical-specific issues documented and backlogged for Sprint 8+",
            "Govmen tenant marked status=active on successful validation",
        ]
    ),
    epic_link=E9, sprint="Sprint 7", assignee="Dev C", priority="Medium",
    story_points=5, labels="onboarding,govmen,testing,sprint7", components="QA,Onboarding")

# ═══════════════════════════════════════════════════════════════
# POST-PROCESS: SET BLOCKING RELATIONSHIPS
# A.Blocks = B means B cannot start until A is done
# ═══════════════════════════════════════════════════════════════
blocking_pairs = [
    # Sprint 1 spikes block dependent stories
    (sp_aurora,          s1_schema),         # DB hosting decision must be made before schema design
    (sp_inngest,         s1_orchestration),  # Orchestration engine decision before wiring
    # Sprint 1 within-sprint dependencies
    (s1_fastapi,         s1_clerk),          # Clerk middleware needs shared Pydantic models first
    (s1_fastapi,         s1_litellm),        # LiteLLM integration needs service scaffold
    # Sprint 2 agent pipeline is sequential
    (s2_persona_agent,   s2_icp_agent),      # ICP needs Persona output
    (s2_icp_agent,       s2_signal_agent),   # Signal needs ICP output
    (s2_prompt_registry, s2_ttlcache),       # TTLCache prompt gen needs registry first
    # Sprint 3 Meta webhook is prerequisite for WhatsApp/Instagram and Facebook
    (s3_meta_webhook,    s3_whatsapp_instagram),
    (s3_meta_webhook,    s3_facebook_leadads),
    # Sprint 4 enrichment pipeline is sequential
    (s4_enrichment,      s4_signals),        # Signals need enriched data
    (s4_signals,         s4_rating_agent),   # Rating Agent needs signal scores
    (s4_rating_agent,    s4_output_schema),  # Output Schema wraps Rating Agent output
    (s4_output_schema,   s4_lineage),        # Lineage writes after score is produced
    # Sprint 5 real-time delivery depends on Pusher spike decision
    (sp_pusher,          s5_realtime_delivery),
    # Sprint 6 feedback is prerequisite for pattern detection and quality metrics
    (s6_feedback_api,    s6_pattern_detection),
    (s6_feedback_api,    s6_quality_metrics),
    # Sprint 7 E2E tests run sequentially (each builds on previous passing)
    (s9_e2e_hot,         s9_e2e_cold),
    (s9_e2e_cold,        s9_e2e_noise),
]

for blocker, blocked in blocking_pairs:
    blocker["Blocks"] = str(blocked["Issue ID"])

# ═══════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("VERIFICATION")
print("="*60)

# 1. Epic Link integrity
print("\n[1] Epic Link integrity check:")
epic_names_set = {r["Epic Name"] for r in rows if r["Issue Type"] == "Epic" and r["Epic Name"]}
failures = []
for r in rows:
    if r["Issue Type"] in ("Story", "Task") and r["Epic Link"]:
        if r["Epic Link"] not in epic_names_set:
            failures.append(f"  FAIL ID={r['Issue ID']} has Epic Link '{r['Epic Link']}' — no matching Epic")
if failures:
    for f in failures: print(f)
else:
    print(f"  OK — all {sum(1 for r in rows if r['Epic Link'])} Epic Links match an Epic Name")

# 2. Blocks ID integrity
print("\n[2] Blocks ID integrity check:")
all_ids = {r["Issue ID"] for r in rows}
block_failures = []
for r in rows:
    if r["Blocks"]:
        bid = int(r["Blocks"])
        if bid not in all_ids:
            block_failures.append(f"  FAIL ID={r['Issue ID']} blocks non-existent ID {bid}")
if block_failures:
    for f in block_failures: print(f)
else:
    print(f"  OK — all {sum(1 for r in rows if r['Blocks'])} Blocks references point to valid Issue IDs")

# 3. Developer overlap per sprint
print("\n[3] Developer assignment per sprint (no overlap check):")
from collections import defaultdict
sprint_devs: dict = defaultdict(lambda: defaultdict(list))
for r in rows:
    if r["Assignee"] and r["Sprint"] and r["Issue Type"] in ("Story", "Task"):
        sprint_devs[r["Sprint"]][r["Assignee"]].append(r["Issue ID"])

all_ok = True
for sprint in sorted(sprint_devs.keys()):
    devs = sprint_devs[sprint]
    dev_summary = ", ".join(f"{dev}={len(ids)}stories" for dev, ids in sorted(devs.items()))
    print(f"  {sprint}: {dev_summary}")
    # Check no story assigned to >1 dev (enforced by single Assignee field — just confirm no blank)
    for r in rows:
        if r["Sprint"] == sprint and r["Issue Type"] == "Story" and not r["Assignee"]:
            print(f"    WARNING: ID={r['Issue ID']} has no assignee")
            all_ok = False

if all_ok:
    print("  No overlap issues found")

# Summary
print(f"\n{'='*60}")
print(f"TOTAL ROWS   : {len(rows)}")
print(f"  Epics      : {sum(1 for r in rows if r['Issue Type'] == 'Epic')}")
print(f"  Stories    : {sum(1 for r in rows if r['Issue Type'] == 'Story')}")
print(f"  Tasks      : {sum(1 for r in rows if r['Issue Type'] == 'Task')}")
total_sp = sum(int(r["Story Points"]) for r in rows if r["Story Points"])
print(f"  Total SP   : {total_sp}")
print(f"{'='*60}\n")

# ═══════════════════════════════════════════════════════════════
# OUTPUT — CSV
# ═══════════════════════════════════════════════════════════════
csv_path = OUTPUT_DIR / "jira_stories.csv"
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
print(f"CSV  written: {csv_path}")

# ═══════════════════════════════════════════════════════════════
# OUTPUT — XLSX (formatted, colour-coded by Issue Type and Sprint)
# ═══════════════════════════════════════════════════════════════
if HAS_OPENPYXL:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Jira Stories"

    # Colour map
    TYPE_FILL = {
        "Epic":    "1F4E79",   # dark blue — white text
        "Story":   "DDEBF7",   # light blue — dark text
        "Task":    "FFF2CC",   # yellow — dark text
    }
    SPRINT_ACCENT = {
        "Sprint 1": "E2EFDA",
        "Sprint 2": "E2EFDA",
        "Sprint 3": "FCE4D6",
        "Sprint 4": "FCE4D6",
        "Sprint 5": "EAF0FB",
        "Sprint 6": "EAF0FB",
        "Sprint 7": "F2E6FF",
    }
    COL_WIDTHS = {
        "Issue ID": 8, "Issue Type": 11, "Summary": 55, "Description": 90,
        "Epic Name": 35, "Epic Link": 35, "Sprint": 10, "Assignee": 10,
        "Priority": 10, "Story Points": 8, "Labels": 28, "Blocks": 7, "Components": 22,
    }

    # Header row
    hdr_fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    hdr_font = Font(color="FFFFFF", bold=True, size=10)
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for ci, col in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=ci, value=col)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = hdr_align

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    # Data rows
    for ri, row_data in enumerate(rows, 2):
        itype = row_data["Issue Type"]
        sprint = row_data.get("Sprint", "")
        bg = TYPE_FILL.get(itype, "FFFFFF")
        row_fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")

        for ci, col in enumerate(COLUMNS, 1):
            cell = ws.cell(row=ri, column=ci, value=row_data[col])
            if itype == "Epic":
                cell.fill = row_fill
                cell.font = Font(color="FFFFFF", bold=True, size=9)
            else:
                # Use sprint accent colour for non-epic rows
                accent = SPRINT_ACCENT.get(sprint, "FFFFFF")
                cell.fill = PatternFill(start_color=accent, end_color=accent, fill_type="solid")
                bold = col == "Summary"
                cell.font = Font(bold=bold, size=9)
            cell.alignment = Alignment(vertical="top", wrap_text=(col == "Description"))

    # Column widths
    for ci, col in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(ci)].width = COL_WIDTHS.get(col, 15)

    xlsx_path = OUTPUT_DIR / "jira_stories.xlsx"
    wb.save(xlsx_path)
    print(f"XLSX written: {xlsx_path}")

print("\nDone.")
