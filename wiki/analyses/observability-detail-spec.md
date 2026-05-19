---
type: analysis
question: "Define the detailed observability specification: step-level logging, trace correlation strategy, replay/debug strategy, alert thresholds with owners, autoscaling triggers, and backup/recovery plan."
date: 2026-05-19
tags: [observability, logging, tracing, alerting, autoscaling, backup, recovery, devops]
sources_consulted:
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/service-scaling-strategy]]"
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/llm-operational-safeguards]]"
  - "[[analyses/security-planning]]"
status: COMPLETE
---

# Observability Detail Specification — Epic 0.11

**Question:** Step-level logging, trace correlation, replay/debug, alert thresholds with named owners, autoscaling triggers, backup/recovery plan.
**Date:** 2026-05-19

This document fills the operational gaps in [[analyses/governance-observability-layer]] (which covers monitoring architecture, metric definitions, and alert triggers) and [[analyses/service-scaling-strategy]] (which covers pool model and crash recovery). Read both before this document.

---

## 1. Step-Level Logging Spec

### 1.1 Two Log Streams

Every step in the pipeline produces output to two distinct streams:

| Stream | Medium | Audience | Retention |
|---|---|---|---|
| **Structured app log** | stdout → **AWS CloudWatch Logs** (Phase 1 locked — see [[analyses/tech-stack-research]]) | Engineering team — debugging, incident response | 30 days hot; archive to cold storage after 30 days |
| **Lineage record** | Postgres (`task_execution` + `lineage_record`) | System — audit trail, quality metrics, replay | 2 years (per data retention policy) |

App logs are for humans debugging in real time. Lineage records are for the system to reconstruct what happened.

**Phase 1 tooling: AWS CloudWatch Logs (locked — per [[analyses/tech-stack-research]]).** The log format (structured JSON, §1.2) and event catalog (§1.3–§1.5) are tool-agnostic; the stdout→CloudWatch path works without code changes if the team upgrades to Grafana Cloud at Phase 2. CloudWatch Logs Insights queries the structured JSON fields directly.

### 1.2 Structured Log Format

All log lines are emitted as JSON to stdout. CloudWatch Logs Insights can query them directly.

```json
{
  "timestamp": "2026-05-19T10:23:45.123Z",
  "level": "INFO",
  "service": "orchestration",
  "correlation_id": "run_a1b2c3d4",
  "tenant_id": "org_gamoft_001",
  "lead_id": "lead_e5f6g7h8",
  "stage": "enrich",
  "event": "enrichment_completed",
  "duration_ms": 1842,
  "fields_populated": 14,
  "sources_called": ["truecaller", "apollo", "surepass"],
  "sources_failed": []
}
```

**Required fields on every log line:**

| Field | Type | Notes |
|---|---|---|
| `timestamp` | ISO 8601 UTC | Always UTC |
| `level` | INFO / WARN / ERROR | ERROR = requires investigation; WARN = expected degradation |
| `service` | ingestion / orchestration / reporting | Which ECS service emitted this |
| `correlation_id` | string | `run_{uuid}` — ties all log lines for one pipeline run |
| `tenant_id` | string | Always present — no cross-tenant log contamination |
| `stage` | string | Current pipeline stage — see stage names below |
| `event` | string | What happened at this stage — see event names below |

`lead_id` is present on all Pipeline 1 logs. It is absent on Pipeline 2 logs (Pipeline 2 is tenant-level, not per-lead).

**PII rule:** `name`, `phone`, `email`, `raw_message` are never included in log fields. If any log event would naturally include these (e.g. a validation error on the phone field), the value is replaced with `[REDACTED]`. See [[analyses/security-planning]] §3.2.

---

### 1.3 Pipeline 1 — Per-Stage Log Events

**Stage: `trigger`** — Lead arrives and pipeline run is created.

| Event | Level | Key fields |
|---|---|---|
| `pipeline_run_created` | INFO | `run_id`, `trigger_source` (channel/manual/rescore), `lead_count` |
| `lead_queued` | INFO | `lead_id`, `channel`, `lead_source` (dm/lead_ad) |

---

**Stage: `data_gather`** — Fetch leads from all connected channels simultaneously.

| Event | Level | Key fields |
|---|---|---|
| `channel_fetch_started` | INFO | `channel` (facebook/instagram/whatsapp/sheets), `tenant_id` |
| `channel_fetch_completed` | INFO | `channel`, `leads_fetched`, `duration_ms` |
| `channel_fetch_failed` | WARN | `channel`, `error_type`, `http_status` (if applicable) |
| `channel_fetch_partial` | WARN | `channel`, `leads_fetched`, `leads_skipped`, `reason` |
| `all_channels_failed` | ERROR | — triggers Critical alert (see §4) |
| `dedup_completed` | INFO | `leads_before_dedup`, `leads_after_dedup`, `dupes_removed`, `dedup_method` (phone/email/name_location) |

---

**Stage: `normalise`** — Message Parser (DM path only), field normalisation.

| Event | Level | Key fields |
|---|---|---|
| `message_parser_called` | INFO | `lead_id`, `model` (haiku), `input_tokens`, `output_tokens` |
| `message_parser_completed` | INFO | `lead_id`, `fields_extracted`, `duration_ms`, `language_detected` |
| `message_parser_failed` | WARN | `lead_id`, `error_type` — lead continues with raw message fields |
| `normalisation_completed` | INFO | `lead_id`, `fields_normalised`, `phone_valid`, `email_valid` |
| `consent_gate_checked` | INFO | `lead_id`, `jurisdiction`, `consent_status` (confirmed/unconfirmed), `enrichment_scope` (full/internal_only) |
| `intent_gate_checked` | INFO | `lead_id`, `intent_score`, `gate_result` (pass/clarification_sent) |
| `clarification_sent` | INFO | `lead_id`, `channel`, `template_used` |

---

**Stage: `enrich`** — External enrichment providers called.

| Event | Level | Key fields |
|---|---|---|
| `enrichment_started` | INFO | `lead_id`, `mode` (b2b/b2c), `sources_planned` (list) |
| `enrichment_source_called` | INFO | `lead_id`, `source`, `endpoint`, `duration_ms` |
| `enrichment_source_completed` | INFO | `lead_id`, `source`, `fields_populated`, `http_status` |
| `enrichment_source_failed` | WARN | `lead_id`, `source`, `error_type`, `attempt_number` |
| `enrichment_source_rate_limited` | WARN | `lead_id`, `source`, `retry_after_ms` |
| `enrichment_completed` | INFO | `lead_id`, `total_fields_populated`, `sources_succeeded`, `sources_failed`, `lead_completeness_score` |

---

**Stage: `score`** — Rating Agent LLM call (Anthropic Claude Sonnet).

| Event | Level | Key fields |
|---|---|---|
| `scoring_started` | INFO | `lead_id`, `prompt_version`, `persona_version`, `variant` (new/returning/rescore), `input_tokens`, `cached_tokens` |
| `scoring_completed` | INFO | `lead_id`, `bucket`, `score`, `lead_completeness`, `needs_review`, `output_tokens`, `latency_ms` |
| `scoring_schema_validation_failed` | WARN | `lead_id`, `attempt_number`, `missing_fields` |
| `scoring_retry` | WARN | `lead_id`, `attempt_number`, `error_type`, `wait_ms` |
| `scoring_failed` | ERROR | `lead_id`, `reason` — triggers routing to `human_review` |
| `scoring_fallback_activated` | WARN | `lead_id`, `fallback_provider` — LiteLLM fallback path |

---

**Stage: `bucketize`** — Bucket assignment, completeness check, disqualification gate.

| Event | Level | Key fields |
|---|---|---|
| `disqualification_checked` | INFO | `lead_id`, `disqualified` (bool), `reason` (if disqualified) |
| `bucket_assigned` | INFO | `lead_id`, `bucket` (HOT/WARM/COLD), `score`, `thresholds_used` |
| `needs_review_flagged` | INFO | `lead_id`, `lead_completeness`, `threshold` |
| `sla_set` | INFO | `lead_id`, `bucket`, `sla_deadline_utc` |

---

**Stage: `deliver`** — Hand off to Delivery and Integration Layer.

| Event | Level | Key fields |
|---|---|---|
| `delivery_started` | INFO | `lead_id`, `bucket`, `delivery_surfaces` (chat/crm/webhook) |
| `lead_card_pushed` | INFO | `lead_id`, `salesperson_id`, `channel` (soketi) |
| `crm_sync_completed` | INFO | `lead_id`, `crm_type`, `duration_ms` |
| `webhook_dispatched` | INFO | `lead_id`, `webhook_id`, `http_status` |
| `delivery_completed` | INFO | `lead_id`, `pipeline_stage` (delivered), `total_run_duration_ms` |

---

**Terminal states (additional events):**

| Event | Level | Key fields |
|---|---|---|
| `lead_routed_human_review` | INFO | `lead_id`, `reason` (scoring_failed/low_completeness/disqualified) |
| `lead_awaiting_clarification` | INFO | `lead_id`, `clarification_sent_at`, `timeout_deadline_utc` |
| `lead_failed` | ERROR | `lead_id`, `last_stage`, `error_type`, `attempts` |

---

### 1.4 Pipeline 2 — Per-Stage Log Events

Pipeline 2 is tenant-level (no `lead_id`). `correlation_id` = `onboarding_run_{uuid}`.

| Stage | Event | Level | Key fields |
|---|---|---|---|
| `persona_agent` | `persona_agent_started` | INFO | `tenant_id`, `trigger` (first_run/rerun), `business_description_length` |
| `persona_agent` | `persona_agent_completed` | INFO | `tenant_id`, `duration_ms`, `persona_version`, `input_tokens`, `output_tokens` |
| `persona_agent` | `persona_agent_failed` | ERROR | `tenant_id`, `error_type`, `attempt_number` |
| `icp_agent` | `icp_agent_started` | INFO | `tenant_id`, `persona_version` |
| `icp_agent` | `icp_agent_completed` | INFO | `tenant_id`, `duration_ms`, `icp_version`, `mode` (b2b/b2c) |
| `signal_agent` | `signal_agent_started` | INFO | `tenant_id`, `persona_version`, `icp_version` |
| `signal_agent` | `signal_agent_completed` | INFO | `tenant_id`, `signals_generated`, `signals_by_dimension`, `duration_ms` |
| `prompt_generation` | `prompt_template_generated` | INFO | `tenant_id`, `prompt_version`, `signal_slots_count`, `template_size_tokens` |
| `onboarding` | `pipeline2_completed` | INFO | `tenant_id`, `total_duration_ms`, `persona_version`, `icp_version`, `signal_count`, `prompt_version` |
| `onboarding` | `pipeline2_failed` | ERROR | `tenant_id`, `failed_stage`, `error_type` — blocks Pipeline 1 |

---

### 1.5 Background Job Log Events

| Job | Key events | Level |
|---|---|---|
| Score Decay | `decay_job_started`, `leads_decayed`, `leads_auto_cold`, `decay_job_completed` | INFO |
| SLA Tracker | `sla_check_started`, `hot_leads_breached`, `alerts_dispatched`, `sla_check_completed` | INFO / WARN (breach) |
| Quality Tracking | `quality_job_started`, `snapshots_written`, `quality_job_completed` | INFO |
| Instagram Token Refresh | `token_refresh_started`, `tokens_refreshed`, `tokens_failed`, `token_refresh_completed` | INFO / ERROR |

---

## 2. Trace Correlation Strategy

### 2.1 The Problem

A single lead's pipeline run touches three ECS services (Ingestion, Orchestration, Reporting) and makes external calls to enrichment APIs and the Anthropic LLM. Without a shared identifier, a log line in Ingestion (`lead_id: lead_abc`) cannot be tied to the corresponding Temporal workflow log in Orchestration unless you search by lead_id across all log groups — which is slow and error-prone.

### 2.2 Solution — Single Correlation ID Per Run

At Pipeline 1 start, the orchestrator generates a `correlation_id`:

```python
import uuid

correlation_id = f"run_{uuid.uuid4().hex[:12]}"
# Example: run_a1b2c3d4e5f6
```

This is the `pipeline_run.id` field in the database. It is propagated:
1. As a log field on every structured log line from any service involved in this run.
2. In HTTP headers when Ingestion calls Orchestration: `X-Correlation-ID: run_a1b2c3d4e5f6`
3. In the Temporal workflow context so every Activity log carries it automatically.
4. In every `task_execution` and `lineage_record` row via the `pipeline_run_id` foreign key.

```python
import structlog

log = structlog.get_logger().bind(
    correlation_id=correlation_id,
    tenant_id=tenant_id,
    lead_id=lead_id,
    stage="enrich",
)
log.info("enrichment_started", sources_planned=["truecaller", "apollo"])
```

### 2.3 Correlation ID Lifecycle

| Event | What happens |
|---|---|
| Pipeline 1 triggered | `correlation_id` generated; `pipeline_run` record created with this id |
| Lead ingested | `correlation_id` written to `leads.current_run_id` field |
| Each service call | `X-Correlation-ID` header passed; receiving service reads it and binds it to its logger |
| Each stage | `task_execution` row created with `pipeline_run_id = correlation_id` |
| LLM call | `correlation_id` included in Anthropic API metadata (via `metadata` param); returned in response headers |
| Run completes | `pipeline_run.status = completed/failed`; `correlation_id` can now be used to reconstruct the full run |

### 2.4 Querying by Correlation ID

**In your log aggregation tool** (exact syntax depends on chosen tool — illustrative example):

```
# Filter all log lines for one pipeline run
filter: correlation_id = "run_a1b2c3d4e5f6"
fields: timestamp, service, stage, event, lead_id, duration_ms
sort: timestamp asc
```

Every log aggregation tool (CloudWatch Logs Insights, Grafana Loki, Datadog, etc.) can execute this filter — `correlation_id` is a top-level JSON field on every log line, making it universally queryable.

**In Postgres** (full lineage for one run):

```sql
SELECT tr.stage_name, tr.started_at, tr.completed_at, tr.status, tr.error_type
FROM task_execution tr
WHERE tr.pipeline_run_id = 'run_a1b2c3d4e5f6'
ORDER BY tr.started_at;
```

This gives the full ordered timeline of every stage, from data_gather to deliver, for any lead in any run.

### 2.5 Pipeline 2 Correlation IDs

Pipeline 2 uses a separate id format: `onboard_{tenant_id}_{timestamp_unix}`. The tenant suffix ties it to the tenant without needing a separate lookup. Example: `onboard_gamoft001_1747600000`.

---

## 3. Replay and Debug Strategy

### 3.1 What "Replay" Means

Replay = re-run a specific lead through the pipeline from a specific stage, using the same inputs that were present at that stage when the original run occurred. Used for:
- Debugging unexpected scores (why did this lead score COLD?)
- Testing a new prompt version against historical leads
- Recovering a failed lead after fixing the underlying enrichment issue

### 3.2 Inspect Before Replay — `inspect_lineage` CLI

Before replaying, understand what happened. The `inspect_lineage` CLI (decided in [[analyses/security-planning]] §Open Decisions) decrypts and pretty-prints the full lineage for a lead:

```bash
python manage.py inspect_lineage --lead-id lead_e5f6g7h8

# Output:
# Run: run_a1b2c3d4e5f6  Tenant: gamoft_001  Lead: lead_e5f6g7h8
# ---
# Stage: data_gather    Status: completed   Duration: 423ms
# Stage: normalise      Status: completed   Duration: 89ms
# Stage: enrich         Status: completed   Duration: 1842ms
#   Fields populated: 14  Completeness: 0.71
# Stage: score          Status: completed   Duration: 3210ms
#   Bucket: COLD  Score: 32  Prompt: v2.1.0  Persona: v1.0.3
#   LLM Input: [decrypted and printed]
#   LLM Output: [decrypted and printed]
# Stage: bucketize      Status: completed
#   Disqualified: false  needs_review: false
# Stage: deliver        Status: completed
```

### 3.3 Force Re-Run From Stage

The orchestrator exposes a management command to force a specific lead through the pipeline from a given stage:

```bash
python manage.py rescore_lead --lead-id lead_e5f6g7h8 --from-stage score
```

`--from-stage` options: `normalise`, `enrich`, `score`, `bucketize`

**What this does:**
1. Creates a new `pipeline_run` with `trigger = "manual_rescore"`.
2. Reads the lead's current state from the database (enriched data, signal values).
3. Re-executes the pipeline from the specified stage forward.
4. All prior stages use the data already stored — no new API calls are made for stages before `--from-stage`.
5. Writes a new `lineage_record` for each re-executed stage.
6. New score overwrites the current score (the old `lead_score` row is retained with `superseded_at` timestamp).

**Why per-stage replay, not full re-run:**
- Full re-run wastes enrichment API quota (Truecaller, Probe42, etc. all charge per call).
- If you know the score is wrong because of a bad prompt version, you only need to re-run from `score` — enrichment data is already correct.
- If enrichment failed for a specific source, re-run from `enrich`.

### 3.4 Staging Environment Replay

For testing a new prompt against historical leads without affecting production:

1. Export the lineage records for the leads you want to test (admin CLI):
   ```bash
   python manage.py export_lineage --tenant-id gamoft_001 --limit 50 --output leads_sample.json
   ```
2. Run the pipeline in `--dry-run` mode against the exported data in staging:
   ```bash
   python manage.py batch_rescore --input leads_sample.json --dry-run
   ```
3. Dry-run writes results to a temporary table (`rescore_preview`) — does not overwrite any live lead data.
4. Compare the preview bucket distribution against the original: `python manage.py compare_rescore --preview-id preview_20260519`.

This is also the mechanism used by the prompt evaluation framework — see [[analyses/prompt-evaluation-framework]] for the golden test set procedure.

---

## 4. Alert Thresholds — Named Owners and Values

### 4.1 Naming Convention

**Owner = the role that receives the alert and is responsible for acting on it.**

| Owner role | Who | Response SLA |
|---|---|---|
| Engineering lead | Gamoft engineer on call | 30 minutes for Critical; 4 hours for High |
| Team lead | Tenant-side team lead (per tenant) | Next business day for Medium; weekly review for Low |
| Platform admin | Gamoft admin (Anishekh at MVP) | Immediate for security events |

### 4.2 Pipeline 1 Operational Alerts

| Alert | Threshold | Priority | Owner | Action |
|---|---|---|---|---|
| All channels failed | Any run where 0 channels return data | **Critical** | Engineering lead | Investigate channel API status immediately; check Secrets Manager for expired tokens |
| Score coverage drop | < 80% leads reach `delivered` or `human_review` in a run | **High** | Engineering lead | Check `task_execution` for failed stages; check Anthropic API status |
| Pipeline failure rate | > 5% leads in `failed` state in a run | **High** | Engineering lead | Check `task_execution` errors; enrichment failures or LLM timeouts |
| Pipeline 2 failure | Any LLM agent in onboarding fails | **High** | Engineering lead | Pipeline 1 cannot run for this tenant until resolved; check agent error in lineage |
| LLM latency p95 | > 8 seconds per scoring call (p95 over 1h window) | **High** | Engineering lead | Check Anthropic API status; consider activating LiteLLM fallback manually |
| Human review queue | > 20% leads routed to `human_review` in a single run | **Medium** | Engineering lead → inform tenant Team lead | Likely enrichment data thinning; check completeness distribution |
| Lead completeness | > 50% leads below 0.50 completeness in a run | **Medium** | Engineering lead | Enrichment degradation; check which sources are failing |
| HOT SLA breach | Any HOT lead uncontacted after 24h | **High** | Team lead (tenant-scoped) | Direct alert to the affected tenant's team lead; salesperson action required |
| Awaiting clarification rate | > 15% leads at Intent Gate in a run | **Low** | Team lead (tenant-scoped) | Monitor for trend; may indicate channel message pattern shift |
| Bucket distribution shift | HOT% changes > ±20pp from 4-week rolling average | **Medium** | Engineering lead + Team lead | Could be lead mix change OR scoring drift; check prompt version and ICP freshness |

### 4.3 Infrastructure Alerts

| Alert | Threshold | Priority | Owner |
|---|---|---|---|
| Service container crash | Any service exits with non-zero code | **High** | Engineering lead |
| Service CPU sustained high | > 85% CPU for > 5 minutes on any service | **Medium** | Engineering lead |
| Database CPU high | > 80% for > 10 minutes | **High** | Engineering lead |
| Database storage | > 80% of provisioned storage | **Medium** | Engineering lead |
| Workflow engine worker down | No heartbeat from workflow worker for > 2 minutes | **Critical** | Engineering lead |
| API error rate | > 2% 5xx responses on any API endpoint over 5 minutes | **High** | Engineering lead |
| Secrets vault access failure | Any failed secret fetch (permission error) | **High** | Platform admin |

### 4.4 Quality Alerts (Post-Month 1)

These alerts use `quality_snapshots` data and require baseline data to be meaningful. Calibrate thresholds after Month 1.

| Alert | Suggested threshold | Priority | Owner |
|---|---|---|---|
| Score coverage rate drop | Week-on-week drop > 10pp | **High** | Engineering lead |
| AP1 Bucket-Outcome Rate decline | Weekly BOR drops > 15pp from prior week | **Medium** | Team lead |
| C1 Cross-run stability | Week-on-week re-score bucket flip rate > 30% | **Medium** | Engineering lead + Team lead |
| Feedback rate drop | Weekly feedback rate < 20% of delivered leads | **Medium** | Team lead |

### 4.5 Alert Delivery (Resolved — see [[analyses/security-planning]])

- **Security alerts** → email (SES/Resend) to platform admin. Slack webhook post-Month 1.
- **Operational alerts (Critical/High)** → email to engineering lead + Slack.
- **Tenant-scoped alerts** → in-app notification to tenant team lead (Soketi push channel).
- **Low/Medium quality alerts** → written to `notification_delivery` table; surfaced in quality dashboard; no push notification.

---

## 5. Autoscaling Triggers

### 5.1 Context

**Implementation is TBD during build** — the specific autoscaling mechanism depends on the chosen container orchestration and database stack. The design below specifies *what metric to trigger on and why* for each service. The actual configuration values (thresholds, cooldowns, min/max instances) are set during build once the infrastructure is chosen.

Three services scale independently: Ingestion, Orchestration+LLM, and Reporting.

### 5.2 Ingestion Service

**What it does:** Receives inbound webhooks (Meta), CSV uploads, and programmatic API calls. Stateless — each request is independent.

**Trigger metric: incoming request rate** (not CPU).

Ingestion tasks spend most of their time waiting on I/O — webhook HMAC validation, JSON parsing, DB writes. CPU stays low even under load. Request count is a leading indicator of capacity need; CPU is a lagging one. Scale out when requests per instance exceed a target rate; scale in when the rate drops and stays down long enough to avoid thrashing.

Scale-in cooldown should be conservative (several minutes) — rapid scale-in and scale-out wastes startup time.

### 5.3 Orchestration + LLM Service

**What it does:** Runs Pipeline 1 and Pipeline 2 workflows. Calls enrichment APIs and the Anthropic LLM. CPU-intensive during scoring (JSON parsing, schema validation).

**Trigger metric: CPU utilization.**

Target CPU around 70% — leaves headroom for burst scoring without over-provisioning. Scale-in cooldown must be **long** (8–10 minutes): workflows are long-running; terminating a container mid-workflow causes a crash recovery cycle. Never scale in aggressively on this service.

**Per-tenant concurrency cap is separate from autoscaling.** The orchestrator enforces a cap of 2 concurrent Scoring Agent calls per tenant regardless of how many instances are running. Autoscaling adds raw capacity; the concurrency cap prevents any tenant from consuming all of it. (Source: [[analyses/service-scaling-strategy]] Rec 9)

If the workflow engine runs as a worker inside the Orchestration service container, each new container instance automatically becomes an additional worker — the workflow engine distributes tasks across all workers.

### 5.4 Reporting Service

**What it does:** Serves dashboard queries and quality report APIs. Reads only from `quality_snapshots` — never from raw pipeline tables (this is a non-negotiable rule — see [[analyses/service-scaling-strategy]] Rec 11). Memory-intensive due to result set buffering.

**Trigger metric: CPU utilization.**

Target CPU around 60% — lower than Orchestration because reporting queries are bursty (team lead opens dashboard → fires several queries at once). A lower target provides faster headroom for bursts.

Scale-in can be aggressive here: reporting load is predictable and business-hours-only at MVP.

### 5.5 Database Scaling

**Implementation depends on chosen database option** (Aurora Serverless, managed RDS, self-hosted PostgreSQL — TBD).

The design principle: the reporting service uses a read-only replica connection string, not the primary writer connection. This prevents report queries from competing with Pipeline 1 writes. How this is provisioned depends on the chosen database.

Whatever database is chosen must support:
- Automated backups
- A read replica or read-only endpoint for the Reporting service
- Point-in-time recovery within at least a 7-day window

---

## 6. Backup and Recovery Plan

**Implementation details are TBD during build** — specific backup mechanisms and recovery times depend on the chosen database and infrastructure stack. The targets and requirements below are tool-agnostic.

### 6.1 RTO and RPO Targets

| Component | RTO target | RPO target |
|---|---|---|
| Application database (PostgreSQL) | < 5 minutes for managed DB with automatic failover; < 30 minutes for self-hosted | < 5 minutes (replication lag on managed); < 24 hours (daily backup on self-hosted) |
| Workflow engine database | < 30 minutes (restore from backup) | < 24 hours (daily backup sufficient) |

**Why these targets are acceptable at MVP:** Even a 5-minute database outage causes only a brief scoring interruption. No leads are permanently lost — `pipeline_stage` crash recovery resumes any in-flight leads automatically on the next run (see [[analyses/orchestration-layer-spec]] §8.4).

### 6.2 Application Database Backup Requirements

Regardless of which database option is chosen, it must satisfy:

| Requirement | Minimum standard |
|---|---|
| Automated daily backups | Must be on by default; no manual intervention |
| Point-in-time recovery | At least 7-day PITR window |
| Long-term cold archive | Monthly `pg_dump` export to object storage (S3, GCS, or equivalent) — covers the 2-year data retention requirement beyond the PITR window |
| Read replica for Reporting service | Required — prevents dashboard queries competing with Pipeline 1 writes |
| Failover | Automatic preferred (managed DB); manual tolerable (self-hosted) |

Monthly cold archive procedure (tool-agnostic):

```bash
# Monthly at 02:00 UTC
pg_dump $DATABASE_URL | gzip > /tmp/full_dump_$(date +%Y-%m).sql.gz
# Upload to object storage of choice (S3, GCS, etc.)
```

### 6.3 Workflow Engine Database Backup

The workflow engine (Temporal or equivalent) maintains its own PostgreSQL database. This stores workflow state and history — separate from the application database.

**Requirements:**
- Daily automated backup to object storage
- 7-day backup retention (workflow state older than 7 days is not needed — application DB has full lead history)
- Recovery procedure: restore latest backup to a new instance; workers reconnect automatically; pipeline_stage crash recovery handles in-flight leads

### 6.4 Recovery Runbook — Primary Database Failure

This procedure is implementation-specific and should be written during build once the database option is confirmed. The tool-agnostic steps are:

1. **Detect:** Alert fires on database connection failure or high CPU (alert defined in §4.3).
2. **Failover:** Promote replica to primary (automatic on managed DB; manual on self-hosted).
3. **Verify:** Check log aggregation for resumed Orchestration service output. Query `SELECT COUNT(*) FROM pipeline_run WHERE started_at > NOW() - INTERVAL '5 minutes'` on the new primary.
4. **Lead recovery:** Any lead mid-pipeline has `pipeline_stage` at a non-terminal value. Crash recovery picks it up on the next Pipeline 1 run automatically.
5. **Escalate:** If failover is not complete within 10 minutes, escalate to database vendor/support.

### 6.5 Application Code Recovery

Application code lives in git. Container rollback is a one-command operation regardless of chosen orchestration (ECS, K8s, Fly, etc.):

| Component | Recovery method | Target time |
|---|---|---|
| Crashed service container | Orchestration layer auto-restarts (desired count maintained) | < 60 seconds |
| Bad deployment | Redeploy previous container image tag | < 3 minutes |
| Workflow engine worker crash | Container auto-restart; workers reconnect to engine | < 60 seconds |

---

## Open Decisions

| Item | Status |
|---|---|
| Log aggregation tooling | **RESOLVED — AWS CloudWatch Logs (Phase 1 locked); Grafana Cloud upgrade eligible at Phase 2** — see [[analyses/tech-stack-research]] |
| Container orchestration (affects autoscaling config) | `[TBD during build — ECS Fargate / K8s / Fly.io / other]` |
| Database option (affects backup mechanism + RTO/RPO actuals) | `[TBD during build — Aurora Serverless / RDS / self-hosted PostgreSQL]` |
| Workflow engine (affects worker restart behaviour) | `[TBD during build — Temporal / Step Functions / Inngest / other]` |
| Alert delivery tooling (SES/Resend for email, Slack webhook) | Resolved in [[analyses/security-planning]] — configure before Tenant 1 onboarding |

---

## Confirmed Decisions

| Decision | Basis |
|---|---|
| Two log streams: structured app log + lineage DB records (`task_execution` + `lineage_record`) | This document 2026-05-19 |
| Structured logs emitted as JSON to stdout — tool-agnostic | This document 2026-05-19 |
| Required log fields: timestamp, level, service, correlation_id, tenant_id, stage, event | This document 2026-05-19 |
| PII never in log fields — REDACTED substitution | [[analyses/security-planning]] §3.2 |
| `correlation_id = pipeline_run.id` — propagated in HTTP `X-Correlation-ID` header and workflow engine context | This document 2026-05-19 |
| Pipeline 2 correlation ID format: `onboard_{tenant_id}_{timestamp_unix}` | This document 2026-05-19 |
| Replay mechanism: `rescore_lead --from-stage` CLI; dry-run via `batch_rescore --dry-run` | This document 2026-05-19 |
| Ingestion scaling metric: incoming request rate (not CPU) | This document 2026-05-19 |
| Orchestration scaling metric: CPU utilization; scale-in cooldown must be long (8–10 min) | This document 2026-05-19 |
| Reporting scaling metric: CPU utilization; aggressive scale-in acceptable | This document 2026-05-19 |
| Database must have: automated backups, PITR ≥ 7 days, read replica, monthly cold archive | This document 2026-05-19 |
| Workflow engine database: daily backup, 7-day retention | This document 2026-05-19 |
| RTO target: < 5 minutes (managed DB) / < 30 minutes (self-hosted) | This document 2026-05-19 |
| RPO target: < 5 minutes (managed DB with replication) / < 24 hours (self-hosted daily backup) | This document 2026-05-19 |
| Alert owners: Critical/High → Engineering lead (30-min SLA); tenant alerts → Team lead | This document 2026-05-19 |
