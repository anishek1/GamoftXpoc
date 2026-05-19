---
type: analysis
question: "Define the DevOps controls missing from epics 0.6–0.9: onboarding feature flags and failure alerts, orchestration monitoring dashboard and job tracking, enrichment scheduler and throttling, context caching and validation logging."
date: 2026-05-19
tags: [devops, feature-flags, monitoring, dashboard, throttling, caching, scheduler, alerting, onboarding]
sources_consulted:
  - "[[analyses/onboarding-flow-stage-map]]"
  - "[[analyses/onboarding-flow-readiness]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/context-construction-specification]]"
  - "[[analyses/enrichment-tools-integration]]"
  - "[[analyses/inngest-function-design]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/observability-detail-spec]]"
  - "[[analyses/security-planning]]"
  - "[[analyses/client-config-schema-defaults]]"
status: COMPLETE
---

# DevOps Controls — Epics 0.6–0.9

**Question:** DevOps controls missing from the four workflow design epics: onboarding (feature flags, failure alerts, logs), orchestration (monitoring dashboard, job tracking), data acquisition (scheduler, throttling, failure logging), and context construction (caching strategy, versioning ops, validation logging).
**Date:** 2026-05-19

Each section maps to one JIRA epic's DevOps controls story. The logical pipeline design for each epic is documented separately — this document covers only the operational controls layer.

---

## Epic 0.6 — Onboarding DevOps Controls

### 0.6.1 Feature Flag Strategy

**What feature flags are for:** Enabling or disabling specific capabilities per tenant without a code deployment. At MVP with 3 POC tenants, flags let you enable a new feature for Gamoft (self-tenant dogfooding) before rolling it to Urvee Organics or Govmen.

**Where flags live:** `tenant_config.feature_flags` — a JSON column in the existing `tenant_config` table. No external feature flag service needed at MVP.

```sql
-- Column already on tenant_config; ensure the column exists
ALTER TABLE tenant_config ADD COLUMN IF NOT EXISTS
  feature_flags JSONB NOT NULL DEFAULT '{}';
```

**Flag format:** `{ "flag_name": boolean }`

```json
{
  "enrichment_surepass":      true,
  "enrichment_probe42":       false,
  "enrichment_tracxn":        false,
  "enrichment_newscatcher":   false,
  "enrichment_serper":        false,
  "score_decay":              true,
  "news_signals":             false,
  "b2b_investigation_path":   true
}
```

**Flag evaluation:** The Orchestrator reads `feature_flags` from `tenant_config` at the start of each Pipeline 1 run. No caching — reads fresh from DB every run. This is deliberate: flags must be togglable without a service restart.

```python
flags = tenant_config.feature_flags
if flags.get("enrichment_tracxn"):
    run_tracxn_enrichment(lead)
```

**Flag management:** Admin sets flags via the config API (`PATCH /tenants/{id}/config`) — same endpoint as other `tenant_config` fields. Only `admin` role can write flags. `team_lead` can read but not write.

**Rollout pattern (three-step):**
1. Enable flag for `org_gamoft_001` only → validate behaviour for 1 week.
2. Enable for one POC tenant (Urvee or Govmen) → validate.
3. Enable for all tenants → flag becomes the new default; eventually remove the flag and make the behaviour unconditional.

**Flag retirement:** When a feature is stable and enabled for all tenants, remove the flag from `feature_flags` and delete the conditional check from application code. Flags that live indefinitely accumulate dead branches.

**Flags are not a substitute for proper onboarding.** A flag that has been `true` for all tenants for 3+ months should be removed from the codebase.

---

### 0.6.2 Onboarding Failure Alerts

**Failure definition:** Any Pipeline 2 stage (Persona Agent, ICP Agent, Signal Agent, Prompt Generation) that fails after 1 retry. This halts the onboarding for the affected tenant — Pipeline 1 cannot run until Pipeline 2 completes. (Source: [[analyses/orchestration-layer-spec]] §Pipeline 2 retry rules)

**Alert contents:**

```json
{
  "alert_type":      "pipeline2_failure",
  "tenant_id":       "org_gamoft_001",
  "correlation_id":  "onboard_gamoft001_1747600000",
  "failed_stage":    "signal_agent",
  "error_type":      "LLMOutputSchemaError",
  "attempt_number":  2,
  "timestamp":       "2026-05-19T10:23:45Z",
  "action_required": "Inspect lineage: python manage.py inspect_lineage --run-id onboard_gamoft001_1747600000"
}
```

**Alert delivery:** Email to engineering lead (same channel as High operational alerts — see [[analyses/observability-detail-spec]] §4.5). Subject line: `[PIPELINE 2 FAILURE] {tenant_id} — {failed_stage}`.

**What blocks until resolved:** The tenant cannot score any leads. `tenant.status` stays at `onboarding` — no leads are delivered. This is a blocking failure.

**Recovery steps:**
1. Run `python manage.py inspect_lineage --run-id {correlation_id}` to see the exact error.
2. Common causes by stage:

| Stage | Common cause | Fix |
|---|---|---|
| `persona_agent` | Business description too vague for LLM to parse | Edit tenant's business description; re-run Pipeline 2 |
| `icp_agent` | Persona output missing required fields | Check persona_agent output in lineage; may be an LLM schema regression |
| `signal_agent` | Too many signals requested (prompt too large) | Reduce signal count in tenant config; re-run |
| `prompt_generation` | Signal count × template size exceeds token budget | Reduce signals or increase tenant's token budget tier |

3. Trigger re-run: `python manage.py run_pipeline2 --tenant-id {tenant_id}` or via admin API `POST /pipeline2/run`.
4. Monitor re-run via job tracking (see §0.7.2).

**Automatic retry on next day:** If the failure is transient (Anthropic API outage), the system does not auto-retry. Engineering lead manually re-triggers after the underlying issue is resolved. Automatic retry of a failed onboarding is not implemented at MVP — the failure almost always requires human diagnosis first.

---

### 0.6.3 Onboarding Audit Logs

Onboarding events are audit-logged to `access_log` per [[analyses/security-planning]] §3.3. The following onboarding-specific events must always be logged:

| Event | What is logged |
|---|---|
| Tenant created | `user_id` (admin), `tenant_id` (new), `action: tenant_created` |
| Pipeline 2 triggered (first run) | `user_id`, `tenant_id`, `trigger: onboarding_initiated` |
| Each Pipeline 2 stage completed | Stage name, duration, `trigger: pipeline2_stage_completed` — written to `task_execution`, not `access_log` (system event, not human action) |
| Pipeline 2 failed | `tenant_id`, `failed_stage`, `error_type` — written to both `task_execution` and triggers alert |
| Tenant activated (`tenant.status → active`) | `user_id` (admin who confirmed), `tenant_id`, `action: tenant_activated` |
| Pipeline 2 re-run triggered | `user_id`, `tenant_id`, `trigger` (manual/feedback-driven), `action: pipeline2_rerun` |
| Feature flag changed | `user_id`, `tenant_id`, `flag_name`, `old_value`, `new_value`, `action: feature_flag_updated` |
| Connector (channel) added | `user_id`, `tenant_id`, `channel`, `action: connector_added` |

Feature flag changes are the most important to audit — they affect which capabilities are active for a tenant and must be traceable to who changed them and when.

---

## Epic 0.7 — Orchestration DevOps Strategy

### 0.7.1 Monitoring Dashboard Metrics

Two dashboards serve different audiences.

**Dashboard 1 — Ops Dashboard (engineering team)**

Reads from a combination of `quality_snapshots` (pre-computed metrics) and real-time queries on `pipeline_run` and `task_execution`. Refreshes every 60 seconds.

| Panel | Metric | Source | Why |
|---|---|---|---|
| Pipeline runs (live) | Count of pipeline_runs in progress right now | `pipeline_run WHERE status = 'running'` | Is the pipeline currently active? |
| Leads in queue | Leads with non-terminal `pipeline_stage` not in `awaiting_clarification` | `leads` real-time query | Pipeline backlog depth |
| Score coverage (last 24h) | % leads reaching `delivered` or `human_review` | `quality_snapshots` | Is the pipeline producing output? |
| Pipeline failure rate (last 24h) | % leads reaching `failed` state | `quality_snapshots` | Are there systemic failures? |
| LLM latency p95 (last 1h) | 95th percentile scoring call duration | Aggregated from `task_execution.duration_ms` WHERE stage = 'score' | LLM performance health |
| Enrichment source health (last 24h) | Per-provider: success rate, avg duration | `task_execution` WHERE stage = 'enrich' | Which enrichment sources are degraded? |
| Human review queue depth | Count of leads in `human_review` right now | `leads WHERE pipeline_stage = 'human_review'` | Growing queue = completeness or scoring problem |
| Awaiting clarification (live) | Count of leads paused at Intent Gate | `leads WHERE pipeline_stage = 'awaiting_clarification'` | Intent Gate volume |
| LLM cost today | Token spend so far today | `lineage_record.input_tokens + output_tokens` aggregated | Daily cost guard |
| Alert history | Last 10 alerts fired | `notification_delivery` or alert log | Recent incidents |

**Dashboard 2 — Tenant Quality Dashboard (team lead, per-tenant)**

Reads from `quality_snapshots` only — no real-time queries, no raw pipeline table access. (Source: [[analyses/service-scaling-strategy]] Rec 11)

| Panel | Metric | Cadence |
|---|---|---|
| Score coverage rate | % leads scored this week | Weekly snapshot |
| Bucket distribution | HOT / WARM / COLD % this week | Weekly snapshot |
| HOT SLA compliance | % HOT leads contacted within 24h | Weekly snapshot |
| Action rate by bucket | % leads actioned per bucket | Weekly snapshot |
| Feedback rate | % delivered leads with feedback this week | Weekly snapshot |
| Lead completeness distribution | % in each band (≥80%, 50–79%, <50%) | Per-run snapshot |
| AP1 Bucket-Outcome Rate | Monthly quality metric (after Month 1) | Monthly snapshot |

**Dashboard tooling:** TBD during build — any tool that can query Postgres or your log aggregation service works (Grafana, Metabase, in-product React dashboard). The underlying data model (`quality_snapshots`) is the same regardless of front-end tool.

---

### 0.7.2 Job Tracking Strategy

**Primary surface: workflow engine UI.**

The workflow engine (Temporal, Inngest, or equivalent — TBD) has a built-in job tracking UI. This is the primary surface for engineering to track:
- Which workflow runs are in progress
- Which stage is currently executing
- Input/output per stage
- Retry history and error messages
- Failed runs and their root cause

No custom job tracking UI is needed at MVP — the workflow engine UI is sufficient for the engineering team.

**Secondary surface: pipeline_run + task_execution tables.**

For visibility without workflow engine access (e.g. team lead wanting to know "did my tenant's onboarding complete?"), the following API endpoints expose job status:

```
GET /pipeline/status/{lead_id}
  → returns pipeline_stage, current_run_id, last_updated_at
  → accessible to: admin, team_lead (own tenant), salesperson (own assigned leads)

GET /tenants/{id}/onboarding-status
  → returns onboarding stage (which Pipeline 2 stage completed), status
  → accessible to: admin, team_lead (own tenant)
```

**Structured log correlation for engineering:**

Every workflow run has a `correlation_id`. To track any specific run in the log aggregation tool:

```
filter: correlation_id = "run_a1b2c3d4e5f6"
sort: timestamp asc
```

This reconstructs the exact sequence of events across all services for one pipeline run. (Full strategy: [[analyses/observability-detail-spec]] §2)

**Job tracking for background jobs (decay, SLA, quality):**

Background jobs emit start/end log events with `correlation_id` = `job_{job_name}_{date}`. Check the log aggregation tool for the most recent `quality_job_completed` or `decay_job_completed` event to confirm jobs are running on schedule. If a job has not run within its expected window, the missing log line is the signal.

---

## Epic 0.8 — Data Acquisition DevOps Controls

### 0.8.1 Scheduler Strategy

Enrichment is **triggered per-lead** as part of Pipeline 1, not batched. A lead enters Pipeline 1 → the Orchestrator runs enrichment for that specific lead within the run. There is no separate scheduled enrichment batch job for lead data.

Background jobs that run on schedule (all managed by the workflow engine's cron/schedule feature):

| Job | Schedule | What it does |
|---|---|---|
| Score Decay | Daily at 02:00 UTC | Applies decay to stale HOT/WARM leads |
| SLA Tracker | Every 1 hour | Checks HOT leads for SLA breach, sends alerts |
| Quality Tracking — per-run cadence | After every Pipeline 1 run completes | Computes per-run metrics → `quality_snapshots` |
| Quality Tracking — weekly cadence | Monday 06:00 UTC | Computes weekly metrics → `quality_snapshots` |
| Quality Tracking — monthly cadence | 1st of month 06:00 UTC | Computes monthly metrics → `quality_snapshots` |
| Instagram token refresh | Every 55 days | Refreshes 60-day Instagram access tokens before expiry |
| Channel polling fallback | Every 15 minutes (per connected tenant) | Polls channels that don't support webhooks (fallback only) |
| Enrichment health snapshot | Daily at 03:00 UTC | Aggregates enrichment source success/failure rates → `quality_snapshots` |

**Scheduler ownership:** All scheduled jobs are defined in the workflow engine's cron configuration. Changes to schedules require a code deployment (schedule definition is in code, not in `tenant_config`).

**Schedule drift detection:** If a background job misses its window (no `{job}_completed` log event within 2× the expected interval), the alert from [[analyses/observability-detail-spec]] §4.3 fires. Engineering lead investigates.

---

### 0.8.2 Throttling and Rate Limit Management

Each enrichment provider has rate limits. The system must not exhaust them — an exhausted quota blocks enrichment for all leads until the window resets.

**Per-provider rate limit inventory:**

| Provider | Known rate limit | Limit window | Enforcement |
|---|---|---|---|
| Tracxn | 100 req/hr (playground); higher on paid | Per hour | Hard — returns HTTP 429 |
| NewsCatcherAPI | Depends on tier (v3 paid) | Per month (subscription) | Soft — cost-based |
| Surepass | TBD (confirm via support call) | TBD | TBD |
| Probe42 | TBD (confirm via support call) | TBD | TBD |
| Serper.dev | 50K queries / $50 plan | Per billing period | Cost-based — no hard limit |
| Truecaller | Depends on plan | Per day | Hard — returns 429 |
| Apollo.io | Depends on plan | Per month | Soft — quota tracking |

**Rate limit tracking mechanism:**

A simple counter per provider, stored in Postgres (not Redis — adding Redis for rate limiting alone is not worth the infrastructure at MVP).

```sql
CREATE TABLE enrichment_quota (
  provider        TEXT        NOT NULL,
  window_start    TIMESTAMPTZ NOT NULL,
  window_duration INTERVAL    NOT NULL,  -- '1 hour', '1 day', etc.
  requests_made   INTEGER     NOT NULL DEFAULT 0,
  quota_limit     INTEGER     NOT NULL,
  PRIMARY KEY (provider, window_start)
);
```

Before each enrichment call, the Orchestrator:
1. Reads the current window's `requests_made` for the provider.
2. If `requests_made >= quota_limit * 0.90` (90% consumed) → log `enrichment_source_rate_limited`, skip this provider for this lead, continue with next provider in fallback chain.
3. If call proceeds → increment `requests_made` atomically.

**Why 90% threshold, not 100%:** Concurrent lead processing means multiple scoring calls can check the counter simultaneously. A 10% buffer prevents all concurrent calls from hitting the exact limit at the same time and some exceeding it before the counter is checked again.

**When all fallback providers are rate-limited:** Lead enrichment completes with whatever data was collected before the rate-limited step. `lead_completeness` reflects the missing data. The lead is scored — possibly with `needs_review = true` if completeness drops below threshold.

**Cost guard (daily cap):**

Each enrichment provider also has a cost cap in `tenant_config`. If daily spend for a provider exceeds the cap, that provider is suspended for the rest of the day (same mechanism as rate limiting). This is the second line of defence after the rate limit counter.

---

### 0.8.3 Enrichment Failure Logging and Health Snapshot

**Per-call failure logging** is already specified in [[analyses/observability-detail-spec]] §1.3 (enrich stage events). Every `enrichment_source_failed` event is a structured log line.

**Daily enrichment health snapshot (new background job):**

Runs at 03:00 UTC. Reads `task_execution` rows from the past 24 hours where `stage = 'enrich'`, aggregates per provider, and writes to `quality_snapshots`:

```sql
-- Written by the enrichment health snapshot job
INSERT INTO quality_snapshots (metric_id, tenant_id, cadence, value, computed_at)
SELECT
  'enrichment_source_health_' || source AS metric_id,
  tenant_id,
  'daily',
  jsonb_build_object(
    'calls_attempted',  COUNT(*),
    'calls_succeeded',  COUNT(*) FILTER (WHERE status = 'success'),
    'success_rate',     ROUND(AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END), 3),
    'avg_duration_ms',  ROUND(AVG(duration_ms))
  ),
  NOW()
FROM task_execution_enrichment_detail   -- view joining task_execution + enrichment source field
WHERE started_at >= NOW() - INTERVAL '24 hours'
GROUP BY source, tenant_id;
```

This populates the "Enrichment source health" panel on the ops dashboard (§0.7.1) and enables the enrichment degradation alert from [[analyses/observability-detail-spec]] §4.2.

**Alert trigger:** If any provider's `success_rate` drops below 50% over a 24-hour window → fires High alert to engineering lead. Likely cause: provider outage, credential expiry, or API schema change.

---

## Epic 0.9 — Context Construction DevOps Controls

### 0.9.1 Context Caching Strategy

**What is cached:** The `PersonaObject` — the tenant-level object produced by Pipeline 2 (persona, ICP, scoring weights, signal definitions). (Source: [[analyses/context-construction-specification]] §4)

**Cache location: in-memory, per-process.** No Redis at MVP.

- Simple Python dict with TTL tracking, scoped to the Orchestration service process.
- Each Orchestration service instance maintains its own in-memory cache.
- TTL: 15 minutes. After expiry, the next call loads fresh from DB.

```python
from cachetools import TTLCache

_persona_cache: TTLCache = TTLCache(maxsize=128, ttl=900)  # 900 seconds = 15 minutes
CACHE_KEY = lambda tenant_id, prompt_version: f"{tenant_id}:{prompt_version}"

def get_persona(tenant_id: str, prompt_version: str) -> PersonaObject:
    key = CACHE_KEY(tenant_id, prompt_version)
    if key in _persona_cache:
        return _persona_cache[key]
    persona = db.load_persona(tenant_id, prompt_version)
    _persona_cache[key] = persona
    return persona
```

**Why not Redis at MVP:**
- 3 POC tenants → 3 cached PersonaObjects per process instance. In-memory is trivially sufficient.
- Redis adds infrastructure, IAM policy, another connection string, and a new failure point.
- When to add Redis: when the Orchestration service scales to multiple instances AND persona staleness within a 15-minute window is causing observable quality issues. This is unlikely before 20+ tenants.

**Multi-instance behaviour (important):**
When the Orchestration service scales to 2+ instances, each instance has its own in-memory cache. A persona update (from a Pipeline 2 re-run) propagates to all instances within 15 minutes via TTL expiry — not instantly. This is documented as the "stale-on-re-run" accepted behaviour in [[analyses/context-construction-specification]] §4. Leads scored on the old persona during the 15-minute window have their `persona_version` recorded in `lineage_record`, so any staleness is visible and traceable.

**Cache key:** `(tenant_id, prompt_template_version)` — same persona with a different prompt version is a different cache entry. This prevents stale prompt references.

**Force-flush on demand (admin CLI):**

```bash
python manage.py flush_persona_cache --tenant-id org_gamoft_001
```

Sends a signal to all Orchestration service instances to evict the cache entry for this tenant. Useful after a critical persona fix that cannot wait up to 15 minutes to propagate. Implementation: all instances subscribe to a Postgres NOTIFY channel (`persona_updated`); the CLI publishes the notification; instances receive it and evict immediately.

---

### 0.9.2 Context Versioning — Operational Procedures

Three version identifiers are recorded per scoring call in `lineage_record`: `prompt_template_version`, `persona_version`, `schema_version`. (Source: [[analyses/context-construction-specification]] §5)

**How version changes propagate without disrupting in-flight calls:**

| Change type | How it propagates | In-flight call behaviour |
|---|---|---|
| Prompt version activated (`draft → active`) | Orchestrator reads active prompt version at call time — no caching. Takes effect on the next scoring call after activation. | In-flight calls use the prompt version they already loaded. Their `lineage_record` records the old version. |
| Persona re-run completes (new `persona_version`) | In-memory cache expires within 15 minutes. New calls get new version. | In-flight calls use the cached version they already loaded. Documented accepted behaviour. |
| `schema_version` bump (OUTPUT_SCHEMA change) | Requires code deployment + prompt activation in sequence. | Deploy new code first, then activate new prompt. Never activate a new schema without the code that handles it. |

**Version rollback procedure:**

If a newly activated prompt version produces bad output (detected via monitoring or team lead report):

1. Reactivate the previous prompt version in `prompt_registry` (set `status = 'active'`, demote current to `'deprecated'`).
2. Alert fires automatically (prompt activation is audited — see [[analyses/security-planning]] §3.3).
3. New calls pick up the reverted version immediately (no cache to flush for prompt versions).
4. Leads scored under the bad version are identified by `lineage_record.prompt_template_version` → trigger manual re-score for affected leads: `python manage.py batch_rescore --prompt-version {bad_version} --from-stage score`.

**Version co-existence window:** During the 15-minute persona cache TTL window after a re-run, two prompt_version + persona_version combinations may coexist in `lineage_record`. This is expected. The combination is always faithfully recorded — no ambiguity in lineage.

---

### 0.9.3 Validation Failure Logging

The pre-send validation gate runs 8 checks before every LLM call. Any failure aborts the call — no LLM cost is incurred. (Source: [[analyses/context-construction-specification]] §5)

**What is logged on validation failure:**

```json
{
  "timestamp": "2026-05-19T10:23:45.123Z",
  "level": "WARN",
  "service": "orchestration",
  "correlation_id": "run_a1b2c3d4e5f6",
  "tenant_id": "org_gamoft_001",
  "lead_id": "lead_e5f6g7h8",
  "stage": "score",
  "event": "pre_send_validation_failed",
  "check_failed": "scoring_weights_sum",
  "error_type": "PersonaInvalidError",
  "detail": "scoring_weights sum = 0.97, expected 1.0 ± 0.001",
  "action": "routed_to_human_review"
}
```

**Written to two places:**
1. Structured app log (WARN level) — for real-time engineering visibility.
2. `task_execution` row for the `score` stage with `status = 'failed'` and `error_type` populated — for audit and quality metric computation.

**Validation failure rate metric:**

The daily quality snapshot job computes, per tenant:

```
validation_failure_rate = COUNT(validation failures) / COUNT(scoring attempts) over 24h
```

Written to `quality_snapshots` as `metric_id = 'context_validation_failure_rate'`.

**Alert trigger:** If `validation_failure_rate` exceeds 5% for any tenant over a 24-hour window → High alert to engineering lead. This almost always indicates a persona schema issue (persona update broke the `scoring_weights` invariant) or a code regression in context assembly.

**Validation failure breakdown by check:**

The daily snapshot also breaks down failures by `check_failed`:

| Most common checks to fail | Likely cause |
|---|---|
| `scoring_weights_sum` | Persona update produced weights that don't sum to 1.0 — weight editing bug |
| `missing_signal_key` | A signal was added to the signal registry but not yet populated by enrichment |
| `token_budget_exceeded` | Tenant's signal count grew too large for their tier's token budget |
| `variant_context_mismatch` | Bug in variant selection logic — `returning` variant sent with null `prior_score` |

---

## Open Decisions

| Item | Status |
|---|---|
| Redis vs in-memory for PersonaObject cache — when to upgrade | `[TBD — upgrade when 20+ tenants or multi-instance staleness causes observable quality issues]` |
| Force-flush implementation (Postgres NOTIFY vs HTTP endpoint) | `[TBD during build — both are valid; Postgres NOTIFY requires no new infrastructure]` |
| Enrichment quota tracking — Postgres counter vs Redis counter | `[TBD during build — Postgres is sufficient at MVP; Redis if counter becomes a write bottleneck]` |
| Dashboard front-end tooling | `[TBD during build — Grafana / Metabase / in-product React; data model is the same regardless]` |

---

## Confirmed Decisions

| Decision | Basis |
|---|---|
| Feature flags live in `tenant_config.feature_flags` JSONB column — no external flag service at MVP | This document 2026-05-19 |
| Flag evaluation: read fresh from DB at Pipeline 1 run start — no caching | This document 2026-05-19 |
| Only `admin` role can write feature flags | [[analyses/security-planning]] §1.3 |
| Rollout order: Gamoft self-tenant → one POC tenant → all tenants → remove flag | This document 2026-05-19 |
| Pipeline 2 failure alert: email to engineering lead with tenant_id, failed_stage, correlation_id, action_required | This document 2026-05-19 |
| Feature flag changes must be audit-logged (`access_log`) | This document 2026-05-19 |
| Ops dashboard reads from quality_snapshots + real-time `pipeline_run`/`task_execution` queries | This document 2026-05-19 |
| Tenant quality dashboard reads from quality_snapshots only — no raw pipeline table access | [[analyses/service-scaling-strategy]] Rec 11 |
| Job tracking primary surface: workflow engine built-in UI | This document 2026-05-19 |
| Background job schedule drift detection: missing log event within 2× expected window → alert | This document 2026-05-19 |
| Enrichment is per-lead (triggered by Pipeline 1), not batched | This document 2026-05-19 |
| Rate limit tracking: Postgres `enrichment_quota` table; 90% threshold triggers skip | This document 2026-05-19 |
| Daily enrichment health snapshot job writes per-provider success rates to quality_snapshots | This document 2026-05-19 |
| Enrichment provider success rate < 50% over 24h → High alert to engineering lead | This document 2026-05-19 |
| PersonaObject cache: in-memory TTLCache (cachetools), 15-min TTL, per-process | This document 2026-05-19 |
| Cache key: (tenant_id, prompt_template_version) | [[analyses/context-construction-specification]] §4 |
| Force-flush: admin CLI command; implementation (Postgres NOTIFY vs HTTP) TBD during build | This document 2026-05-19 |
| Prompt version rollback: reactivate previous version in prompt_registry; takes effect immediately | This document 2026-05-19 |
| Validation failure rate > 5% over 24h → High alert to engineering lead | This document 2026-05-19 |
| Validation failures logged to: structured app log (WARN) + task_execution (status=failed) | This document 2026-05-19 |
