---
type: analysis
question: "What is the complete agile build blueprint for the Multi-Tenant Adaptive Lead Intelligence Engine — the definitive reference for what to build, in what order, and how to validate it?"
date: 2026-05-20
tags: [blueprint, epics, agile, build-sequence, sprint-plan, mvp, architecture, planning]
sources_consulted:
  - "[[analyses/service-boundaries]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/scoring-quality-metrics]]"
  - "[[analyses/execution-type-classification]]"
  - "[[analyses/lead-enrichment-architecture]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/security-planning]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/observability-detail-spec]]"
  - "[[analyses/devops-controls]]"
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/inngest-function-design]]"
  - "[[analyses/onboarding-flow-readiness]]"
  - "[[analyses/prompt-template-framework]]"
  - "[[analyses/meta-integration-implementation]]"
  - "[[analyses/core-use-cases]]"
  - "[[analyses/test-strategy]]"
  - "[[analyses/mvp-scope-sign-off]]"
  - "[[analyses/operational-business-kpis]]"
  - "[[analyses/api-contract]]"
  - "[[analyses/dev-environment-requirements]]"
  - "[[analyses/context-construction-specification]]"
  - "[[analyses/action-relevance-metrics]]"
status: COMPLETE
---

# Master Development Blueprint — Multi-Tenant Adaptive Lead Intelligence Engine

**Question:** What is the complete agile build blueprint — what to build, in what order, and how to validate it?
**Date:** 2026-05-20

---

## Part 1 — System Summary

The Multi-Tenant Adaptive Lead Intelligence Engine is a SaaS platform that scores inbound leads in real time for multiple business tenants using a combination of deterministic enrichment and LLM-driven reasoning. Each tenant has a unique AI-generated persona, ideal customer profile, and signal definitions that determine how leads from their channels (WhatsApp, Instagram, Facebook, email) are scored and routed. The system produces ranked lead cards delivered to salespeople, routes low-quality or ambiguous leads to human review, and collects outcome feedback to continuously improve scoring accuracy. The three POC tenants are Gamoft (B2B self-tenant), Urvee Organics (B2C, Instagram + WhatsApp), and Govmen (business type TBD — blocked until tenant interview). The core value proposition is measurably better lead prioritisation than manual triage, validated by conversion lift and salesperson feedback rate within 2 consecutive weeks of live operation.

---

## Part 2 — Architecture at a Glance

### Services

The system has **8 services**. (Note: [[analyses/service-boundaries]] states "7 owned services" in its summary line but enumerates 8 — the enumerated list is authoritative.)

| Service | Responsibility |
|---|---|
| Ingestion Service | Receives leads from all channels; validates, deduplicates, pre-filters |
| Enrichment Service | Calls 9 external providers; applies consent gate and quota tracking |
| Profile Service | Manages PersonaObject, ICP definitions, signal definitions per tenant |
| Scoring Agent Service | Hosts Rating Agent (Sonnet) + Output Schema Layer |
| Orchestration Service | Drives Pipeline 1 stage-by-stage; owns lineage write order; crash recovery |
| Reporting Service | Quality snapshots, dashboards, scheduled reports, admin CLI |
| Feedback Service | Collects salesperson outcomes; attributes to signals; detects patterns |
| Onboarding Service | Drives Pipeline 2 (Persona → ICP → Signal → Prompt); manages tenant lifecycle |

### Two Pipelines

**Pipeline 2 — Tenant Onboarding** (runs once per tenant, admin-triggered):

Five formal stages:
- Stage 1: Account Creation
- Stage 2: Org Setup
- Stage 3: Business Profile submission → Pipeline 2 async execution (Persona Agent → ICP Agent → Signal Agent → Prompt Generation → Prompt Evaluation)
- Stage 4: Connector Setup (channel OAuth, API token configuration)
- Stage 5: Readiness Check → `tenant.status = 'active'`

**Pipeline 1 — Per-Lead Scoring** (continuous, per lead):
`captured` → `fetched` → `enriched` → `normalised` → `scored` → terminal state

Terminal states: `delivered` | `existing_customer` | `human_review` | `awaiting_clarification` | `insufficient_signal` | `failed`

### Five LLM Agents

| Agent | Model | Pipeline | Purpose |
|---|---|---|---|
| Persona Agent | Sonnet 4.6 | Pipeline 2 | Infer PersonaObject from business profile |
| ICP Agent | Sonnet 4.6 | Pipeline 2 | Infer ideal customer profile |
| Signal Agent | Sonnet 4.6 | Pipeline 2 | Generate signal definitions per scoring dimension |
| Rating Agent | Sonnet 4.6 | Pipeline 1 | Score lead 0–100; return sub-scores, bucket, recommended_action, reasoning |
| Message Parser | Haiku | Pipeline 1 | Classify DM as LEAD / NOISE / EXISTING_CUSTOMER / UNCLEAR; extract structured fields |

### Lineage Write Order — Crash-Safety Guarantee

Every pipeline stage writes in this exact order:
`lineage_record` → `task_execution` → `pipeline_run` → **`pipeline_stage` (always last)**

The Orchestration Service resumes from `pipeline_stage` on crash. No stage is re-run unnecessarily.

### Tech Stack

**Locked decisions:**

| Component | Decision |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI + Uvicorn |
| Package manager | uv |
| LLM primary | Anthropic Claude Sonnet 4.6 |
| LLM fallback | OpenAI GPT-4o via LiteLLM |
| Auth | Clerk (JWT + webhooks) |
| Secrets | AWS Secrets Manager |
| Observability | AWS CloudWatch Logs (Phase 1) |
| Compute | AWS ECS Fargate |
| PII encryption | AES-256-GCM (name, phone, email, location, raw_message) |

**Decisions finalized Sprint 1:**

| Component | Candidates | Decision point |
|---|---|---|
| Workflow orchestration | Inngest (current strong candidate) vs Temporal | Sprint 1 |
| PostgreSQL hosting | Aurora Serverless vs EC2-hosted Postgres | Sprint 1 |
| Real-time delivery | Pusher vs Soketi | Sprint 1 |

### Security Model

Three layers applied on every request:
1. **Postgres RLS** — row-level isolation enforced at DB; `SET LOCAL app.tenant_id` set by middleware
2. **Clerk JWT** — token validated on every request; `tenant_id` and `role` extracted
3. **4-role RBAC** — `admin`, `team_lead`, `salesperson`, `viewer`; viewer sees aggregated metrics only, never raw PII

### Data Model

32 core entities (see [[sources/2026-core-business-entities]]) + `enrichment_quota` table (33rd entity — tracks per-provider API usage per tenant; 90% threshold triggers alert; provider not called at 100%).

### Enrichment Providers

9 providers with per-tenant feature flag control:
Truecaller · Apollo.io · Surepass (GSTN/CIN/PAN) · Probe42 · Tracxn · NewsCatcherAPI · IndiaMART/JustDial · Serper.dev (Google fallback) · Google Places

---

## Part 3 — Epic Catalogue

---

### Epic 1 — Foundation

**Goal:** Every service boots, auth middleware rejects unauthenticated requests, and the CI pipeline is green. All Sprint 2+ work builds on this skeleton.

**Capabilities:**
- Monorepo structure, uv workspaces, per-service Dockerfile
- PostgreSQL schema + migrations (Alembic or equivalent — finalize Sprint 1): all 32 core entities + `enrichment_quota` (33rd) + RLS policies per-tenant
- FastAPI skeleton: each of the 8 services has `GET /health`, shared Pydantic models matching the data model, shared error response shape
- Clerk JWT middleware: validates token, extracts `tenant_id` and `role`, sets Postgres session variable (`app.tenant_id`) for RLS activation
- LiteLLM proxy: routes to Anthropic primary; OpenAI fallback on provider error; structured error propagation
- Workflow orchestration: Inngest (or Temporal — finalize Sprint 1) local dev wiring; at least one test function fires and completes end-to-end
- AWS Secrets Manager integration: all API keys fetched from vault at service startup; local dev bypass via `SECRETS_MANAGER_ENABLED=false`
- Structured JSON logging: every service emits `{timestamp, level, service, correlation_id, tenant_id, stage, event}` to stdout → CloudWatch from day one
- CI pipeline: unit test runner, linter (ruff), type checker (mypy); PR gate enforced

**Acceptance Criteria:**
- All 8 services start without errors in local dev
- `GET /health` returns 200 on every service
- Any unauthenticated request to a protected endpoint returns 401
- RLS isolation: query with `SET LOCAL app.tenant_id = 'X'` cannot read tenant Y's rows
- One workflow function fires and completes in local dev
- CI pipeline passes on a clean branch

**Depends On:** Nothing — first epic.

**Wiki:** [[analyses/tech-stack-research]], [[analyses/security-planning]], [[analyses/service-boundaries]], [[analyses/dev-environment-requirements]]

---

### Epic 2 — Tenant Onboarding (Pipeline 2)

**Goal:** An admin can onboard a new tenant end-to-end; the system produces a locked PersonaObject, ICP definition, signal definitions, and a versioned prompt template in `active` status — ready for Pipeline 1.

**Capabilities:**
- Onboarding API endpoints: create org, submit business profile, get readiness check, trigger Pipeline 2, get onboarding status
- Persona Agent (Sonnet): infers PersonaObject (full schema with `inference_flags`, staleness metadata, B2B/B2C mode) from business profile input
- ICP Agent (Sonnet): infers ideal customer profile from PersonaObject + `business_type`
- Signal Agent (Sonnet): generates signal definitions per scoring dimension (Fit, Intent, Engagement, Behaviour, Context) for the tenant
- Prompt generation: fills prompt template slots from signal definitions + PersonaObject; commits to `prompt_registry` with semantic version
- Prompt evaluation framework: draft → evaluation → active lifecycle; a prompt cannot transition to `active` without passing evaluation (schema compliance, sub-score sum, bucket consistency — see [[analyses/test-strategy]])
- Tenant config JSONB: feature flags per provider, scoring dimension weights, bucket thresholds (default HOT ≥ 80, WARM ≥ 55), enrichment toggles
- Pipeline 2 re-run: admin or team_lead triggers; new prompt version generated; previous version deactivated
- Prompt rollback: reactivating a prior `prompt_registry` version takes immediate effect — no restart required
- `tenant.status` lifecycle: `onboarding` → `active`; Pipeline 1 enqueues but does not execute while `onboarding`
- Queue drain on activation: all leads captured during `onboarding` window are processed in order when status transitions to `active`
- PersonaObject TTLCache: in-memory (cachetools), 15-min TTL, cache key = `(tenant_id, prompt_template_version)`; force-flush triggered by Postgres NOTIFY on prompt version change

**Acceptance Criteria:**
- Gamoft onboarded: PersonaObject, ICP, signals, prompt template all in `active` status
- Urvee Organics onboarded (B2C mode, distinct weights and ICP)
- Pipeline 2 re-run produces a new prompt version without disrupting active Pipeline 1 runs
- Prompt rollback: deactivate current, reactivate prior — Pipeline 1 picks up prior version within one TTL cycle
- `tenant.status = 'onboarding'` blocks Pipeline 1 execution; leads queue; activation drains in order

**Depends On:** Epic 1

**Wiki:** [[analyses/onboarding-flow-readiness]], [[analyses/prompt-template-framework]], [[analyses/llm-io-contract]]

---

### Epic 3 — Lead Ingestion

**Goal:** Leads arrive from all MVP channels and land in `captured` state with correct `source_channel`, `raw_message`, and initial metadata. NOISE is filtered before any enrichment or LLM cost is incurred.

**Capabilities:**
- Meta webhook receiver: HMAC-SHA256 signature validation (`X-Hub-Signature-256`), per-channel payload parsing, idempotency key to deduplicate Meta's at-least-once delivery
- WhatsApp: Embedded Signup OAuth + WABA token per tenant; DM and Business API paths
- Instagram: Instagram Login OAuth; 60-day token refresh background job (token expiry is a production risk — job must be in place before go-live)
- Facebook: Page token (non-expiring)
- Lead Ads (all 3 Meta surfaces): enter pipeline at Stage 3 (enrichment), bypass Message Parser entirely
- Email inbound: basic parsing for lead extraction
- Google Sheets / CSV upload: LLM-assisted column mapping for historical data
- Two-stage lead filtering (DM path only):
  1. Rule filter — regex/heuristics; cheap, eliminates obvious non-leads
  2. Message Parser (Haiku) — classifies as LEAD / NOISE / EXISTING_CUSTOMER / UNCLEAR; extracts structured fields for LEAD
- NOISE path: `pipeline_stage = 'insufficient_signal'` set immediately; zero enrichment calls; zero LLM scoring calls; discard event written to `intake_event_log` with `discard_reason`; discard rate metric incremented
- Webhook + polling hybrid: polling fallback fires when Meta webhook delivery is delayed or dropped; event deduplication by `platform_event_id` ensures idempotency at the DB write level; both mechanisms run in parallel — webhooks primary, polling is failsafe
- EXISTING_CUSTOMER routing (locked 2026-05-22): `pipeline_stage = 'existing_customer'` (terminal); CRM sync event emitted; no scoring; no lead card created. See [[analyses/orchestration-layer-spec]] §8.1
- UNCLEAR routing (locked 2026-05-22): `pipeline_stage = 'awaiting_clarification'`; lead paused; salesperson notified to send clarifying message; 24h timeout via workflow engine `waitForEvent`; exempt from crash recovery and score decay while paused
- Deduplication: phone match wins; email second; name + location fallback; duplicate merged, not double-counted
- Pre-flight validation: missing active persona → HALT; missing signal definitions → HALT; missing active prompt template → HALT
- Pydantic validation on inbound payload: HTTP 422 on unknown or malformed fields

**Acceptance Criteria:**
- WhatsApp DM with valid HMAC signature passes; tampered payload returns 403
- NOISE DM (`pipeline_stage = 'insufficient_signal'`) fires zero enrichment and zero LLM calls
- Lead Ad payload bypasses Message Parser, enters at enrichment stage with correct `source_channel`
- Duplicate lead (same phone, different arrival time) is merged — not stored twice
- Pre-flight HALT: lead with no active prompt template does not proceed past `captured`
- Instagram 60-day token refresh job is in place, scheduled, and unit-tested against a mocked clock (live expiry verification requires a 60-day window — job correctness is the acceptance criterion, not waiting for expiry)
- Polling fallback: a lead missed by webhook but caught by poll is ingested exactly once (dedup by `platform_event_id` prevents double-processing)

**Depends On:** Epic 1, Epic 2 (pre-flight requires active persona and prompt)

**Wiki:** [[analyses/meta-integration-implementation]], [[analyses/llm-io-contract]], [[analyses/orchestration-layer-spec]], [[analyses/channel-integration-layer]]

---

### Epic 4 — Lead Scoring (Pipeline 1 Core)

**Goal:** Every lead that passes pre-flight is enriched, normalised, scored by the Rating Agent, bucketed, and has a full lineage record at every stage. PII encryption is applied here — this is the first point at which lead data is persisted.

**Note on PII encryption placement:** AES-256-GCM encryption of `name`, `phone`, `email`, `location`, and `raw_message` is implemented in this epic at the repository layer — when leads are first written to the database. Epic 7 audits and hardens but does not introduce PII encryption for the first time.

**Capabilities:**
- PII encryption at rest: AES-256-GCM on `name`, `phone`, `email`, `location`, `raw_message` — encrypted at repository layer on first write; decrypted only at repository layer on read; `REDACTED` substitution in all log output
- Consent Gate: jurisdiction check + `consent_status` evaluated before any external enrichment provider is called; `consent_status = 'revoked'` → enrichment scope = `internal_only`
- Enrichment service — 9 providers:
  - Per-tenant feature flags control which providers are active for each run
  - Fallback chain fires on empty response (e.g. Apollo empty → Serper.dev)
  - `enrichment_quota` table updated per call; 90% threshold alert fired; provider skipped and signals recorded as `not_detected` at 100%
- Normalisation stage: E.164 phone format, ISO 8601 dates, city-tier mapping (1 / 2 / 3), Title Case names
- Signal extractors — all 13 types: deterministic (AUTOMATION execution type); each returns `(detected: bool, value: float, evidence: str)` for the same input every time (see [[analyses/signal-detection-rule-spec]] for named extractor definitions)
- Rating Agent (Sonnet): receives `INPUT_SCHEMA` (lead data + signals + PersonaObject + prompt); returns `OUTPUT_SCHEMA` (score 0–100, bucket, sub-scores across 5 dimensions, `recommended_action` enum, `reasoning` sub-fields)
- Output Schema Layer (HYBRID — deterministic wrapper around LLM output):
  - Banding enforcement: LLM-returned bucket overridden by tenant-configured thresholds (e.g. LLM returns `hot`, score = 72, HOT threshold = 80 → bucket overridden to `warm`)
  - Completeness gate: `lead_completeness < **0.60**` → `needs_review = true` (threshold locked — team decision 2026-05-22; see [[analyses/llm-io-contract]])
  - Schema coercion: lowercase bucket values, round score to integer
- Bucketize stage: score ≥ 80 → HOT; score ≥ 55 → WARM; score < 55 → COLD
- Disqualification gate: geography penalty (−30), role mismatch penalty (−40), spam → force score to 0; rules are per-tenant `DisqualRule[]` typed config; stacking order: `force_zero` > `score_cap` > `score_delta`; clamped to 0 (see `DisqualRule` TypedDict schema in [[docs/phase0/pipeline-io-contracts]])
- Intent gate: `intent_specificity = very_low` AND `fit = HIGH` → `pipeline_stage = 'awaiting_clarification'`; 24h timeout via workflow engine `waitForEvent`; salesperson notified to send clarifying message
- `needs_review = true` → `pipeline_stage = 'human_review'`; lead routed to human review queue
- Score decay background job: −10 points after 7 days, −20 after 14 days, auto-COLD after 30 days; delta adjustment (not full rescore); bucket recomputed after each decay event; new `lineage_record` written with `decay_reason`; SLA clock restarts only on bucket upgrade; `awaiting_clarification` leads exempt while paused (see [[concepts/score-decay]] for full locked mechanics)
- SLA timers started at bucket assignment: HOT = 24h, WARM = 48h, COLD = weekly
- Lineage write order (crash-safety): `lineage_record` → `task_execution` → `pipeline_run` → `pipeline_stage` (always last); Orchestration Service resumes from `pipeline_stage` on restart
- PersonaObject TTLCache: 15-min TTL; force-flush via Postgres NOTIFY when prompt version changes
- Per-tenant concurrency cap: default **5** concurrent Scoring Agent calls per tenant (locked — team decision 2026-05-22); configurable via `tenant_config.concurrency_cap`

**Acceptance Criteria:**
- PII fields encrypted in DB; plaintext never visible in any log line (automated scan confirms `REDACTED`)
- Consent Gate: `consent_status = 'revoked'` → zero external enrichment provider calls
- Enrichment fallback: Apollo returns empty → Serper.dev called automatically
- Quota alert: provider at 90% → alert fired; at 100% → provider skipped, signal = `not_detected`
- Rating Agent output passes `OUTPUT_SCHEMA` validation at 100% on golden test set
- Banding enforcement: LLM `bucket = hot`, score = 72, threshold = 80 → system stores `warm`
- Crash recovery: orchestrator killed mid-enrichment → resume from `enriched` stage on restart; no stage re-run unnecessarily
- Golden path 1 (HOT B2B lead): score ≥ 80, bucket = `hot`, `recommended_action = call_immediately`, `delivered` stage reached within 120 seconds of message arrival
- Golden path 2 (COLD SMB fragmented lead): score 35–50, `needs_review = true`, `pipeline_stage = human_review`

**Depends On:** Epic 1, Epic 2, Epic 3

**Wiki:** [[analyses/orchestration-layer-spec]], [[analyses/llm-io-contract]], [[analyses/scoring-quality-metrics]], [[analyses/execution-type-classification]], [[analyses/lead-enrichment-architecture]], [[analyses/devops-controls]]

---

### Epic 5 — Delivery & Salesperson UI

**Goal:** Scored leads reach salespeople as ranked lead cards in real time; HOT leads trigger push notifications; human review and awaiting-clarification queues are visible and actionable.

**Capabilities:**
- Real-time lead card delivery: push to salesperson via real-time layer (Pusher vs Soketi — finalized Sprint 1, implemented this sprint)
- HOT lead push notification to salesperson's device at `delivered` stage
- Awaiting-clarification notification: salesperson prompted to send a clarifying message to the lead; 24h timeout handled by workflow engine
- Human review queue: `team_lead` sees all `pipeline_stage = 'human_review'` leads; card includes qualification note (e.g. "Ask for GST number or formal business name to verify")
- Role-scoped dashboards: quality dashboard (team_lead), action metrics (salesperson), aggregated metrics only for viewer (no raw PII fields rendered)
- CRM sync: Salesforce + HubSpot outbound field mapping
- Outbound webhooks: fixed JSON schema, HTTPS endpoints only
- Scheduled reports: weekly and monthly tenant quality summary
- SLA breach alert: HOT lead with no salesperson action at 24h → alert to `team_lead`

**Acceptance Criteria:**
- HOT lead card appears in salesperson UI within 120s of `pipeline_stage = 'delivered'`
- Push notification fires for HOT bucket; does not fire for WARM or COLD
- Viewer role renders no raw `name`, `phone`, or `email` — aggregated metrics only
- Human review queue shows all `needs_review = true` leads with qualification note populated
- SLA breach: HOT lead reaches 25h without salesperson feedback → `team_lead` alert fired

**Depends On:** Epic 4

**Wiki:** [[analyses/delivery-integration-layer]], [[analyses/security-planning]], [[analyses/operational-business-kpis]]

---

### Epic 6 — Feedback Loop & Governance

**Goal:** Salesperson outcomes flow back to scoring quality measurement; governance layer tracks full lineage, detects signal weight patterns, and surfaces calibration recommendations to team lead.

**Capabilities:**
- Feedback collection API: salesperson submits outcome per lead (`converted` / `not_interested` / `wrong_fit` / `already_known` / etc.)
- Feedback attribution: maps outcome to the specific signals and `prompt_version` that produced the score
- Pattern detection: identifies signals consistently over- or under-weighting versus outcomes across a window of leads
- Team lead recommendation surface: "consider adjusting weight for signal X" surfaced in team_lead dashboard; admin can trigger Pipeline 2 re-run from recommendation
- Scoring quality metrics suite:
  - Score Coverage, AP1–AP4, C1–C5, AR1–AR5, 3 Global KPIs (see [[analyses/scoring-quality-metrics]])
  - **AP1 and AP2 require ~30 days of outcome data — these metrics are not meaningful before Month 2**
- `quality_snapshots` table: written per pipeline run; includes pipeline coverage, bucket stability, failed rate
- Lineage audit: `access_log` append-only, 5-year retention; write failure does NOT halt the primary API request — failure escalated via dead letter mechanism (3 retries at 30s / 5m / 30m; on exhaustion: `failed_audit_log` table insert + CRITICAL CloudWatch metric + admin alert); see [[analyses/security-planning]] §Dead Letter
- Admin CLI suite (see [[analyses/observability-detail-spec]]):
  - `inspect_lineage <lead_id>` — full stage-by-stage trace with model, prompt_version, signals at each stage
  - `rescore_lead <lead_id> --from-stage <stage>` — re-run pipeline from a given stage without re-fetching or re-enriching upstream stages
  - `export_lineage <lead_id>` — export full lineage to JSON
  - `batch_rescore --dry-run` — simulate rescoring a cohort without committing results
  - `compare_rescore` — compare before/after score distributions for a cohort
- `daily_enrichment_health_snapshot` background job: per-provider success rate, latency p50/p95, quota consumption

**Acceptance Criteria:**
- Salesperson submits feedback; pattern detection attributes outcome to contributing signals within one detection cycle
- `access_log` write failure: primary API request completes successfully; failure appears as CloudWatch metric
- `inspect_lineage <lead_id>` returns full trace with `model`, `prompt_version`, signals at every stage
- `rescore_lead --from-stage normalised` re-runs from normalisation; does not re-call enrichment providers
- Quality snapshot written per run; pipeline coverage and bucket stability visible in team_lead dashboard

**Depends On:** Epic 4, Epic 5

**Wiki:** [[analyses/scoring-quality-metrics]], [[analyses/governance-observability-layer]], [[analyses/operational-business-kpis]]

---

### Epic 7 — Security Hardening

**Goal:** Production-grade security posture. Hardens everything scaffolded in Epic 1 and makes PII handling audit-ready across all services. Does NOT introduce PII encryption for the first time — that is Epic 4.

**Capabilities:**
- PII field audit: verify AES-256-GCM encryption applied consistently on every entity added in Epics 3–6; fix any missed fields
- Automated PII key rotation procedure: manual at MVP (documented for 3 tenants); document the rotation procedure for 10+ tenant scale
- RBAC enforcement audit: verify every endpoint gated by the correct role(s); test role escalation attempts
- Cross-tenant isolation adversarial test: construct queries with wrong `tenant_id` and verify RLS returns 0 rows
- REDACTED substitution audit: automated scan of all CloudWatch log streams for any PII pattern (phone, email, name)
- Secrets vault audit: confirm no API key or secret is present in any environment variable in the production environment; all fetched from AWS Secrets Manager
- Webhook signature hardening: replay attack protection — timestamp embedded in signature; requests with timestamp > 5 minutes old rejected with 403
- Session management: Clerk token expiry, refresh flow, role-change revocation
- Security alert: email notification on critical events (repeated auth failures, RLS violation attempts)

**Acceptance Criteria:**
- Zero PII in any CloudWatch log stream (automated pattern scan passes)
- RLS adversarial: direct SQL with wrong `tenant_id` returns 0 rows
- All API keys confirmed fetched from AWS Secrets Manager in production; zero secrets in env vars
- Replay attack: replayed webhook with timestamp > 5 minutes returns 403

**Depends On:** Epic 1 (security scaffold), Epic 4 (PII encryption in place — this epic audits it)

**Wiki:** [[analyses/security-planning]], [[analyses/governance-observability-layer]]

---

### Epic 8 — Observability & DevOps

**Goal:** System is fully observable in production; autoscaling responds to real load; CI/CD promotes to staging and production with enforceable gates; admin tooling is production-ready.

**Capabilities:**
- CloudWatch dashboards: per-service error rates, pipeline stage latency, enrichment provider latency and error rate, LLM call latency and cost per tenant
- Alert system: email for security + critical ops alerts; in-app for tenant-scoped alerts; thresholds defined per metric
- Autoscaling:
  - Ingestion Service: scales on request rate
  - Orchestration Service: scales on CPU with 8–10 minute cooldown (prevents thrashing on bursty lead arrivals)
  - Reporting Service: scales on CPU (aggressive scale-up for batch jobs)
- CI/CD promotion gates:
  - Staging: all unit + integration tests pass + E2E golden paths pass
  - Production: manual approval gate (engineering lead or admin)
- Automated DB backups: schedule and retention configured for production
- `correlation_id` propagation audit: verify every log line for a single lead across all 8 services carries the same `correlation_id`
- `daily_enrichment_health_snapshot` job outputs to CloudWatch metric stream (feeds enrichment provider dashboard)
- Admin CLI tools production-ready and documented: `inspect_lineage`, `rescore_lead`, `batch_rescore --dry-run`, `compare_rescore`
- Runbook: on-call procedures defined for each alert type

**Acceptance Criteria:**
- Kill one enrichment provider's API: CloudWatch alert fires within 2 minutes
- `correlation_id` present on every log line for a traced lead across all services
- Merge to main triggers staging deployment; staging gates pass; production deploy requires manual approval
- Ingestion Service scales up under load test and scales down within cooldown window

**Depends On:** Epic 1 (logging scaffold), all prior epics (complete system to observe)

**Wiki:** [[analyses/observability-detail-spec]], [[analyses/devops-controls]], [[analyses/tech-stack-research]]

---

### Epic 9 — Testing & POC Validation

**Goal:** Full test suite in place and gating PRs; all 3 E2E golden paths pass; system runs for 2 consecutive weeks meeting every POC sign-off condition simultaneously.

**Capabilities:**
- Unit tests:
  - Signal extractors — 100% coverage (highest priority; bugs silently corrupt all scores)
  - Output Schema Layer banding — 100% coverage
  - All AUTOMATION pipeline components — 90%+ (see [[analyses/test-strategy]] Layer 1 for full component table)
- Integration tests: all scenarios in [[analyses/test-strategy]] Layer 2 table — enrichment mocks, pipeline stage transitions, LLM mocked outputs, HMAC signature validation, RLS enforcement, crash recovery
- E2E golden paths (no mocks, real pipeline, dedicated test tenant):
  - **Golden path 1 — HOT B2B lead:** WhatsApp DM with explicit buying intent; verified company via Apollo; score ≥ 80; bucket = `hot`; `recommended_action = call_immediately`; `delivered` within 120s; lineage record at every stage
  - **Golden path 2 — COLD SMB fragmented lead:** Unverifiable company; score 35–50; `needs_review = true`; `pipeline_stage = human_review`; qualification note on lead card
  - **Golden path 3 — NOISE early exit:** Single emoji or greeting; `pipeline_stage = insufficient_signal`; zero enrichment calls; zero LLM scoring calls; zero lead cards created
- LLM evaluation suite: 10+ synthetic leads per bucket (HOT B2B, WARM B2B, COLD B2B, COLD SMB, NOISE); schema compliance 100%; sub-score sum 100%; bucket consistency 100%; triggered on any PR changing a prompt, signal definition, model version, or I/O schema version
- CI/CD gates enforced: PR = unit + integration; merge to main = full suite + E2E + LLM eval
- Govmen onboarding: complete Pipeline 2 and verify scoring end-to-end (contingent on tenant interview being completed — see Part 7)
- 2-week POC monitoring: track pipeline coverage, bucket stability, failed rate, HOT SLA compliance continuously
- Business validation: track conversion per tenant, Scoring Lift, salesperson feedback rate

**Acceptance Criteria — POC Sign-Off (all must be simultaneously true for 2 consecutive weeks):**

Technical:
- Pipeline coverage ≥ 80% (leads reach `delivered` or `human_review` per run)
- Bucket stability ≥ 85% (same bucket on consecutive scoring runs)
- Failed state rate < 2%
- HOT SLA compliance ≥ 80% (contacted within 24h)
- Zero cross-tenant data leaks confirmed by audit log review

Business:
- ≥ 1 HOT lead converted per active tenant (team lead confirmed)
- Scoring Lift > 1.5 (AP2 Discrimination Ratio — requires ~30 days of outcome data; POC sign-off is Month 2–3 earliest)
- Salesperson feedback rate ≥ 30% of delivered leads
- Team lead verbal or written sign-off per tenant

**Depends On:** All prior epics

**Wiki:** [[analyses/test-strategy]], [[analyses/mvp-scope-sign-off]], [[analyses/scoring-quality-metrics]]

---

## Part 4 — Build Sequence & Dependency Map

### Linear Dependency Chain

```
Epic 1 — Foundation
    │
    ▼
Epic 2 — Tenant Onboarding (Pipeline 2)
    │
    ▼
Epic 3 — Lead Ingestion
    │
    ▼
Epic 4 — Lead Scoring (Pipeline 1 Core)    ← PII encryption introduced here
    │
    ├──────────────────────┐
    ▼                      ▼
Epic 5 — Delivery       Epic 7 — Security Hardening
    │                   (can begin once Epic 4 stable)
    ▼
Epic 6 — Feedback & Governance
    │
    └──── Epic 8 — Observability & DevOps
          (can begin once Epic 4 stable)

Epic 9 — Testing & POC Validation
(unit + integration run continuously from Epic 1; E2E and LLM eval gate after Epic 4)
```

### Cross-Cutting Threads

These are not discrete epics — they are threads woven through the entire build:

| Thread | Epic 1 | Epic 4 | Epic 7 |
|---|---|---|---|
| Security | Scaffold: Clerk middleware, RLS policies, secrets vault | PII encryption at rest, consent gate | Harden: audit, adversarial tests, replay protection |

| Thread | Epic 1 | Epic 8 |
|---|---|---|
| Observability | Scaffold: structured logging, correlation_id | Harden: dashboards, alerts, autoscaling, runbook |

| Thread | Epic 1–4 | Epic 9 |
|---|---|---|
| Testing | Unit + integration continuous | E2E golden paths, LLM eval suite, POC monitoring |

**Key parallelism opportunity:** Epics 7 and 8 can begin in parallel with Epic 5/6 once Epic 4 is stable. They harden and observe a working pipeline — they do not depend on delivery or feedback being complete.

---

## Part 5 — Sprint Plan

Sequence and parallelism. No durations — the team sets its own velocity. Three developers.

---

### Sprint 1 — Foundation (Epic 1)

Three parallel tracks from day 1:

- **Dev A:** DB schema + Alembic migrations + RLS policies (all 33 entities, per-tenant row isolation verified)
- **Dev B:** FastAPI scaffolding + Clerk JWT middleware + 4-role RBAC (shared auth dependency for all 8 services)
- **Dev C:** LiteLLM proxy setup + workflow orchestration local dev wiring + AWS Secrets Manager integration + structured logging scaffold

Sprint 1 key decision: **workflow orchestration (Inngest vs Temporal) locked by end of sprint.** All Sprint 2+ workflow code depends on this.

Sprint 1 deliverable: All 8 services boot; auth middleware rejects unauthenticated requests; CI green; workflow orchestration decision locked.

---

### Sprint 2 — Tenant Onboarding (Epic 2)

- **Dev A:** Onboarding API endpoints + tenant config JSONB + `tenant.status` lifecycle + queue drain on activation
- **Dev B:** Persona Agent + ICP Agent + Signal Agent (LLM calls through LiteLLM)
- **Dev C:** Prompt generation + `prompt_registry` versioning + prompt evaluation framework + prompt rollback procedure + PersonaObject TTLCache

Sprint 2 deliverable: Gamoft onboarded end-to-end; Pipeline 2 re-run works; prompt rollback works; Urvee Organics onboarding in progress.

---

### Sprint 3 — Lead Ingestion (Epic 3)

- **Dev A:** Meta webhook receiver + HMAC-SHA256 validation + WhatsApp DM path + Instagram OAuth + 60-day token refresh background job + polling fallback service (runs parallel to webhooks; event dedup by `platform_event_id`)
- **Dev B:** Facebook DM + Lead Ads path (all 3 Meta surfaces) + email inbound + Google Sheets/CSV upload with LLM column mapping
- **Dev C:** Two-stage filter (rule filter + Message Parser Haiku) + deduplication + pre-flight validation + `insufficient_signal` path + `intake_event_log` writes

Sprint 3 note: **EXISTING_CUSTOMER and UNCLEAR routing is RESOLVED (locked 2026-05-22):** EXISTING_CUSTOMER → `existing_customer` (terminal, CRM sync, no scoring); UNCLEAR → `awaiting_clarification`. Dev C implements per [[analyses/orchestration-layer-spec]] §8.1. No sprint decision required.

Sprint 3 deliverable: All channels deliver leads to `captured`; NOISE exits cleanly with zero downstream calls; deduplication working; 60-day Instagram token refresh job running.

---

### Sprint 4 — Lead Scoring (Epic 4)

This is the most complex sprint — the entire pipeline core.

- **Dev A:** Enrichment service (9 providers, per-tenant feature flags, fallback chain, consent gate) + `enrichment_quota` tracking + PII encryption at repository layer
- **Dev B:** Signal extractors (all 13 types) + normalisation stage + disqualification gate + Rating Agent (Sonnet) call via LiteLLM + Input/Output schema validation
- **Dev C:** Output Schema Layer (banding, completeness gate, coercion) + bucketize + lineage write order + crash recovery + score decay job + SLA timers + `awaiting_clarification` flow + per-tenant concurrency cap

Sprint 4 note: **`needs_review` threshold locked at 0.60** (team decision 2026-05-22). Dev C implements completeness gate with this value. See [[analyses/orchestration-layer-spec]] §4.3.

Sprint 4 deliverable: Golden path 1 (HOT B2B) works end-to-end; crash recovery verified; PII confirmed encrypted (automated log scan clean).

---

### Sprint 5 — Delivery & Salesperson UI (Epic 5)

- **Dev A:** Real-time lead card delivery via chosen real-time layer + HOT push notification
- **Dev B:** Human review queue UI + awaiting-clarification salesperson notification + role-scoped dashboards
- **Dev C:** CRM sync (Salesforce + HubSpot) + outbound webhooks + scheduled reports + SLA breach alerts

Sprint 5 deliverable: Golden path 2 (COLD SMB) routes to human review queue; salesperson sees HOT card within 120s; SLA breach alert fires correctly.

---

### Sprint 6 — Feedback & Governance (Epic 6) + Security Hardening (Epic 7) in parallel

- **Dev A:** Feedback collection API + attribution logic + pattern detection + team lead recommendation surface
- **Dev B:** Quality metrics (`quality_snapshots`, AP/C/AR series) + admin CLI suite + `daily_enrichment_health_snapshot` job
- **Dev C (Epic 7):** PII field audit across all entities, RBAC enforcement audit, cross-tenant RLS adversarial test, REDACTED log scan, secrets vault audit, webhook replay protection

Sprint 6 deliverable: Feedback loop functional; quality metrics visible in dashboard; security posture hardened and adversarial tests passing.

---

### Sprint 7 — Observability & DevOps (Epic 8) + Testing & Validation (Epic 9)

- **Dev A:** CloudWatch dashboards + alert thresholds + autoscaling configuration + runbook
- **Dev B:** CI/CD staging + production promotion gates + automated DB backups + `correlation_id` propagation audit
- **Dev C:** E2E golden path 3 (NOISE) + LLM evaluation suite + full test coverage audit + Govmen onboarding (if tenant interview completed)

Sprint 7 deliverable: All 3 E2E golden paths pass; CI/CD gates enforced; system enters POC monitoring window.

---

### POC Monitoring Window

Not a sprint — 2 consecutive weeks of live operation. All 3 developers available for:
- Bug fixes and SLA compliance monitoring
- Salesperson feedback rate tracking
- Business validation (converted HOT leads per tenant)
- Govmen final onboarding (if still pending)

POC sign-off when all technical and business conditions in Part 6 are simultaneously true.

---

## Part 6 — MVP Definition & POC Sign-Off

**MVP = all 3 POC tenants scoring leads end-to-end with measurable quality improvement over 2 consecutive weeks.**

### Technical Conditions

All must be simultaneously true for 2 consecutive weeks:

| Condition | Target |
|---|---|
| Pipeline coverage | ≥ 80% of leads reach `delivered` or `human_review` per run |
| Bucket stability | ≥ 85% of leads score into the same bucket on consecutive runs |
| Failed state rate | < 2% |
| HOT SLA compliance | ≥ 80% of HOT leads contacted within 24h |
| Cross-tenant isolation | Zero `access_log` entries showing a user accessing another tenant's data |
| Tenant onboarding | All 3 tenants onboarded (if Govmen still blocked, Gamoft + Urvee Organics sufficient to begin monitoring) |

### Business Conditions

All must be simultaneously true for 2 consecutive weeks:

| Condition | Target |
|---|---|
| HOT lead conversion | ≥ 1 confirmed converted HOT lead per active tenant |
| Scoring Lift | > 1.5 (AP2 Discrimination Ratio — requires ~30 days of outcome data; earliest Month 2–3) |
| Feedback rate | ≥ 30% of delivered leads have salesperson feedback submitted |
| Team lead sign-off | Each tenant's team lead confirms scoring is "better than what we had before" |

### Sign-Off Process

1. Engineering lead confirms all technical conditions met for 2 consecutive weeks
2. Product owner (Anishekh) reviews business conditions
3. Each POC tenant's team lead signs off verbally or in writing
4. Admin marks MVP complete; system transitions from POC to production

---

## Part 7 — Pre-Build Prerequisites

These must be in place before Sprint 1 begins. Start immediately — some have unknown lead times.

| Prerequisite | Blocks | Action |
|---|---|---|
| Meta developer app created; Embedded Signup configured; webhook domain registered; Facebook, Instagram, WhatsApp permissions approved | Epic 3 | **Start immediately** — app review takes **2–7 days for a clean submission; Business Verification can take up to 60 days** — do not wait |
| Clerk account: organisation created, JWT template configured, webhook endpoint registered | Epic 1 | Start now |
| AWS account: Secrets Manager namespace, CloudWatch log groups, ECS Fargate cluster provisioned | Epic 1 | Start now |
| Anthropic API key (production) | Epics 2, 4 | Start now |
| OpenAI API key (LiteLLM fallback) | Epic 4 | Start now |
| **Surepass credentials** — API access via support call; lead time unknown | Epic 4 | **Start immediately** |
| **Probe42 credentials** — API access via support call; lead time unknown | Epic 4 | **Start immediately** |
| Apollo.io account + API key | Epic 4 | Start now |
| Truecaller Business API access | Epic 4 | Start now |
| **IndiaMART / JustDial API access** — requires business verification; lead time unknown; confirm whether scraping restrictions apply | Epic 4 | **Start immediately** |
| Govmen tenant interview completed | Epic 9 (Govmen onboarding) | Must complete before Sprint 7 |
| Workflow orchestration decision (Inngest vs Temporal) | Epic 2+ | Finalize end of Sprint 1 |
| Real-time delivery decision (Pusher vs Soketi) | Epic 5 | Finalize end of Sprint 1 |
| PostgreSQL hosting decision (Aurora Serverless vs EC2 Postgres) | Epic 1 migrations | Finalize end of Sprint 1 |

---

## Part 8 — Deferred Decisions (Post-MVP)

| Item | Unlock Condition |
|---|---|
| Adaptive Signal Lifecycle (signal integrity scoring, automated discovery, business-language signal UX — Add-ons 6/7/8) | Month 3+ with sufficient scoring history |
| Recommendation Agent (personalised outreach generation) | After Month 3; quality metrics stable |
| Workflow Agent (lead lifecycle orchestration beyond scoring) | After Month 6 |
| Self-serve tenant onboarding | Scaling beyond 3 known POC tenants |
| LinkedIn as a channel | Separate epic post-MVP (API restrictions not justified for POC scale) |
| SAML / enterprise SSO | On-request from a tenant (Clerk supports it; enable then) |
| Mobile app | Post-MVP product decision |
| Redis caching | 20+ tenants or multi-instance PersonaObject staleness issues |
| Silo infrastructure model (per-tenant DB) | Premium tier tenant request |
| Dedicated read replica per tenant | Per-tenant reporting latency becomes measurable problem |
| Automated PII key rotation | 10+ tenants or SOC 2 preparation |
| Grafana Cloud upgrade (Phase 2) | Month 3+ or tenant count justifies (no code changes required; stdout → CloudWatch path is tool-agnostic) |
| Custom outbound webhook format per tenant | On-request |
| Multi-model routing beyond Anthropic + OpenAI | Model performance divergence at scale |

**Hard limits that are never in scope regardless of product direction:**
- Scraping any website or platform — API-only data acquisition, permanently
- Storing credentials in the database — vault path reference only, permanently
- Returning raw PII to viewer role — aggregated metrics only, permanently
- Cross-tenant data access — RLS enforces this at DB level, permanently

---

## Part 9 — Open Questions (Dev Team Resolves During Build)

These are genuine open decisions. Do not resolve them in this document — resolution belongs in the build.

1. **Workflow orchestration — Inngest vs Temporal:** Finalize by end of Sprint 1. Both are architecturally compatible; [[analyses/inngest-function-design]] describes the 8 required functions in Inngest terms — use as reference regardless of which is chosen.

2. **PostgreSQL hosting — Aurora Serverless vs EC2-hosted Postgres:** Finalize by end of Sprint 1.

3. **Real-time delivery — Pusher vs Soketi:** Finalize by end of Sprint 1.

4. **EXISTING_CUSTOMER and UNCLEAR routing:** **RESOLVED 2026-05-22** — EXISTING_CUSTOMER → `existing_customer` (terminal, CRM sync, no scoring); UNCLEAR → `awaiting_clarification`. See [[analyses/orchestration-layer-spec]] §8.1 stage transitions.

5. **`needs_review` threshold:** **RESOLVED 2026-05-22** — locked at **0.60**. Completeness gate in Output Schema Layer: `lead_completeness < 0.60` → `needs_review = true` → `pipeline_stage = 'human_review'`.

6. **E2E test environment:** Dedicated staging environment vs local Docker Compose. Decide before Sprint 7 begins — E2E golden paths run in Sprint 7 and require the environment to be in place. (Deferred to development time per team decision 2026-05-22.)

7. **LLM evaluation suite trigger policy:** **RESOLVED 2026-05-22** — only on PRs that change a prompt template, signal definition, LLM model version, or I/O schema version. Not on every PR. See [[analyses/test-strategy]].

8. **Python testing framework:** pytest assumed. Confirm before Sprint 1 test scaffold.

9. **Migration tool:** Alembic assumed for PostgreSQL schema migrations. Confirm before Sprint 1 DB work.
