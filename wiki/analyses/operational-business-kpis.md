---
type: analysis
question: "What are the operational KPIs (system health) and business KPIs (value delivery) for the Lead Intelligence Engine, and how are they measured?"
date: 2026-05-19
tags: [kpis, operational, business, metrics, monitoring, dashboard, mvp]
sources_consulted:
  - "[[sources/2026-lead-intelligence-engine-reference]]"
  - "[[analyses/scoring-quality-metrics]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/devops-controls]]"
  - "[[analyses/observability-detail-spec]]"
  - "[[analyses/mvp-scope-sign-off]]"
  - "[[analyses/service-scaling-strategy]]"
  - "[[analyses/llm-operational-safeguards]]"
status: COMPLETE
---

# Operational and Business KPIs

**Question:** What are the operational KPIs (system health) and business KPIs (value delivery), and how are they measured?
**Date:** 2026-05-19

This document covers system-level operational KPIs and product-level business KPIs. It does **not** repeat the scoring quality metrics (AP1–AP4, C1–C5, AR1–AR5) which are documented in [[analyses/scoring-quality-metrics]]. The three layers together form the complete performance picture.

---

## 1. Three-Layer KPI Architecture

```
Layer 3: Business KPIs
  └── Is the system delivering business value? (product + management view)

Layer 2: Scoring Quality KPIs   [see analyses/scoring-quality-metrics]
  └── Is the AI producing good scores? (team lead + product view)

Layer 1: Operational KPIs
  └── Is the system running correctly? (engineering view)
```

Each layer has a different cadence, owner, and data source. All three layers must be healthy simultaneously for MVP sign-off to occur.

---

## 2. Operational KPIs

These measure system health and engineering correctness. They live on the **Ops Dashboard** (engineering-only view) documented in [[analyses/devops-controls]] §2.

### KPI Definitions

| ID | KPI | Definition | Target | Alert Threshold | Owner |
|---|---|---|---|---|---|
| **OP1** | Lead Processing Latency p95 | Wall-clock time: `pipeline_run.created_at` → `pipeline_run.completed_at`, 95th percentile | < 120s | > 300s for 5 consecutive leads | Engineering lead |
| **OP2** | LLM Call Latency p95 | Rating Agent HTTP response time, 95th percentile, 10-minute rolling | < 8s | > 15s | Engineering lead |
| **OP3** | Pipeline Success Rate | % of leads reaching `delivered` or `human_review` within a run (not `failed`) | ≥ 98% | < 95% over any 1-hour window | Engineering lead |
| **OP4** | Enrichment Provider Availability | Per-provider: successful API calls / total calls, 1-hour rolling | ≥ 90% per provider | < 50% for any provider over 1 hour | Engineering lead |
| **OP5** | Background Job Completion Rate | % of scheduled background jobs completing within 2× their scheduled window | ≥ 98% | Any job missing for 2 consecutive windows | Engineering lead |
| **OP6** | Cost per Lead | (LLM token cost + enrichment API cost) per successfully scored lead, 7-day rolling average | < $0.05 | > $0.10 | Engineering lead |
| **OP7** | Queue Depth | Leads waiting to enter Pipeline 1 at any moment | < 50 | > 200 | Engineering lead |

### OP1 — Lead Processing Latency p95

**Data source:** `pipeline_run` table.

```sql
SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (
  ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at))
) AS p95_latency_seconds
FROM pipeline_run
WHERE tenant_id = $tenant_id
  AND created_at >= NOW() - INTERVAL '1 hour'
  AND status IN ('completed', 'human_review');
```

**Why 120s target:** The six-stage Pipeline 1 includes two LLM calls (Haiku for DM path, Sonnet for scoring). Haiku adds ~2s; Sonnet adds ~5–8s; enrichment adds up to ~30s for the full B2B stack. 120s leaves buffer for network and queue overhead without implying slowness to the salesperson.

**Why 300s threshold:** Beyond 300s, the HOT lead 24-hour SLA (AR1) is at risk if multiple leads are queuing. Alert triggers re-prioritisation of HOT lead jobs.

---

### OP2 — LLM Call Latency p95

**Data source:** `task_execution` table, `stage = 'score'`, field `duration_ms`.

```sql
SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (
  ORDER BY duration_ms
) AS p95_ms
FROM task_execution
WHERE stage = 'score'
  AND started_at >= NOW() - INTERVAL '10 minutes';
```

**Why separate from OP1:** LLM latency can spike due to provider issues without the overall pipeline being slow (e.g., enrichment cache hits are fast, so the average masks the LLM spike). Tracking it separately enables the LiteLLM fallback trigger documented in [[analyses/llm-operational-safeguards]].

**Alert action:** If > 15s p95, check provider status page. If provider degraded, LiteLLM failover to OpenAI GPT-4o activates automatically. Engineering lead confirms failover is working.

---

### OP3 — Pipeline Success Rate

**Data source:** `quality_snapshots` (System Health row) — do not query `pipeline_run` directly from the reporting service.

**Calculation:**
```
success_rate = (delivered_count + human_review_count) / total_leads_processed
```

Leads in `failed` state count against this rate. Leads in `awaiting_clarification` are excluded (not yet resolved).

**Note:** This is the same metric used in the MVP sign-off condition (`failed` rate < 2% → success rate ≥ 98%). The `quality_snapshots` write happens after each Pipeline 1 run; the ops dashboard reads from there.

---

### OP4 — Enrichment Provider Availability

**Data source:** `enrichment_quota` table (tracks calls and failures per provider per day) + `task_execution` (per-call outcomes).

```sql
SELECT
  provider_name,
  successful_calls::float / NULLIF(total_calls, 0) AS availability
FROM enrichment_quota
WHERE quota_date = CURRENT_DATE
  AND tenant_id = $tenant_id;
```

**Note:** The 90% threshold in the `enrichment_quota` table (documented in [[analyses/devops-controls]] §3) is a rate-limit throttle, not an availability alert. Availability is a separate metric tracking provider-side failures vs. our-side throttling.

**Per-provider targets:**

| Provider | Tier | Availability Target |
|---|---|---|
| Truecaller | T1 (sync) | ≥ 95% |
| Google Places | T1 (sync) | ≥ 95% |
| Surepass | T2 (sync) | ≥ 90% |
| Apollo.io | T2 (sync) | ≥ 90% |
| Probe42 | T3 (async investigation) | ≥ 85% |
| Tracxn | T3 (async investigation) | ≥ 85% |
| NewsCatcherAPI | T3 (async investigation) | ≥ 85% |
| Serper.dev | Fallback | ≥ 80% |

---

### OP5 — Background Job Completion Rate

**Data source:** `task_execution` log events. Each background job emits `job.started` and `job.completed` (or `job.failed`) events. A job is "missing" if `job.completed` is not logged within 2× its scheduled window.

**Background job schedule reference** (from [[analyses/devops-controls]] §3.2):

| Job | Schedule | 2× Window |
|---|---|---|
| score_decay | Daily 02:00 | 48 hours |
| sla_breach_check | Every 30 min | 60 min |
| enrichment_quota_reset | Daily 00:00 | 48 hours |
| persona_cache_warmup | On Pipeline 2 completion | N/A (event-driven) |
| quality_snapshot | Every 6 hours | 12 hours |
| enrichment_health_snapshot | Daily 03:00 | 48 hours |
| scheduled_report | Weekly/monthly per tenant | +24 hours |
| crm_sync_retry | Every 15 min | 30 min |

**Alert:** Any job missing for 2 consecutive windows → High alert to engineering lead. `sla_breach_check` missing → Critical (escalates immediately; HOT SLA compliance at risk).

---

### OP6 — Cost per Lead

**Data source:** Two components combined:

1. **LLM cost** — from token usage logs (input tokens × input price + output tokens × output price per provider rate card). Logged in `task_execution.metadata` for the `score` stage.
2. **Enrichment cost** — from enrichment API invoices (monthly total / monthly leads scored). Computed as a background job.

**Why track at MVP with only 3 tenants:** The $0.05 target calibrates against the enrichment cost model in [[analyses/lead-enrichment-architecture]] (~$180–270/mo for 3 tenants) and the LLM cost estimate in [[analyses/tech-stack-research]] (~$27/mo). At 3 tenants processing ~500 leads/month combined, target is achievable. This becomes a business constraint at scale.

**Note:** Cost per lead is an engineering-read operational metric at MVP. It becomes a business-read metric when billing per tenant is introduced post-MVP.

---

### OP7 — Queue Depth

**Data source:** Workflow engine queue length (specific metric name depends on workflow engine chosen — TBD during build; see [[analyses/observability-detail-spec]] Open Decisions).

**Conceptual threshold logic:** At MVP with 3 tenants and low volume, queue depth > 200 indicates either a processing bottleneck or a runaway data source (e.g., a Lead Ad form with thousands of submissions). Alert triggers investigation before HOT leads are delayed.

---

## 3. Business KPIs

These measure whether the system is delivering value to tenants and their salespeople. They live on the **Tenant Quality Dashboard** (team lead view) and the **Scheduled Reports** (admin/product view).

### KPI Definitions

| ID | KPI | Definition | Target | Owner |
|---|---|---|---|---|
| **BK1** | Tenant Activation Rate | Tenants with `status = active` who have processed ≥ 1 lead / total tenants onboarded | 100% (3/3 POC tenants) | Admin |
| **BK2** | Time-to-Value | Days from Pipeline 2 completion → first confirmed HOT lead converted to sale | < 30 days per tenant | Product / admin |
| **BK3** | HOT Lead Conversion Rate | `feedback_record.outcome = converted` on HOT leads / total HOT leads delivered | Establish baseline Month 1; target 2× COLD rate by Month 3 | Team lead per tenant |
| **BK4** | Scoring Lift | HOT conversion rate / COLD conversion rate (same as AP2 Discrimination Ratio) | > 1.5 (MVP sign-off condition) | Product |
| **BK5** | Salesperson Adoption | % of delivered leads that have ≥ 1 feedback record submitted by a salesperson | ≥ 30% | Team lead per tenant |
| **BK6** | Cost per Converted Lead | Total monthly system cost / total confirmed lead conversions that month | Decreasing month-over-month | Admin |

---

### BK1 — Tenant Activation Rate

**Data source:** `tenant.status` column.

**MVP context:** This is a binary condition for the 3 POC tenants. All 3 must reach `status = active` before the MVP sign-off period begins. Govmen is currently blocked (see [[analyses/mvp-scope-sign-off]] §5).

---

### BK2 — Time-to-Value

**Measurement:**
```
time_to_value = first_converted_feedback_date - pipeline_2_completion_date
```

**Data source:** `feedback_record` (filter: `outcome = converted`, `original_bucket = HOT`) joined to `pipeline_run` (tenant's first run after `tenant.status = active`).

**Why < 30 days:** A salesperson must action a HOT lead within 24h (AR1). A converted lead typically closes within days to weeks for the industries in scope (organic products, B2B software). If no conversion occurs in 30 days, it indicates either scoring quality issues (HOT leads are not actually hot) or salesperson adoption issues.

---

### BK3 — HOT Lead Conversion Rate

**Data source:** `feedback_record` table.

```sql
SELECT
  COUNT(*) FILTER (WHERE outcome = 'converted') AS conversions,
  COUNT(*) AS total_hot,
  COUNT(*) FILTER (WHERE outcome = 'converted')::float / NULLIF(COUNT(*), 0) AS hot_conversion_rate
FROM feedback_record fr
JOIN pipeline_run pr ON fr.pipeline_run_id = pr.id
WHERE pr.tenant_id = $tenant_id
  AND pr.bucket = 'HOT'
  AND fr.submitted_at >= NOW() - INTERVAL '30 days';
```

**Month 1 goal:** Establish the baseline rate. Do not set a target before you have data.

**Month 3 goal:** HOT conversion rate ≥ 2× COLD conversion rate. This is the AP2 Discrimination Ratio > 1.5 sign-off condition from [[analyses/mvp-scope-sign-off]].

**Note:** Feedback is voluntary. The 30% adoption threshold (BK5) is the prerequisite for BK3 being statistically meaningful. If BK5 < 30%, BK3 is unreliable.

---

### BK4 — Scoring Lift

**Definition:** BK4 is identical to the AP2 Discrimination Ratio defined in [[analyses/accuracy-proxy-metrics]]:

```
Scoring Lift = HOT_conversion_rate / COLD_conversion_rate
```

It is listed here as a business KPI because it is the primary signal for the product team (does the score actually discriminate good leads from bad ones?) and is the single most important metric in the MVP sign-off checklist.

**Target:** > 1.5 for MVP sign-off. A ratio of 1.0 means scoring is random. A ratio of 1.5 means HOT leads convert 50% more often than COLD leads — meaningful signal.

**Why it is not tracked in real-time:** Requires accumulated conversion data (feedback loop). Meaningful only after Month 1 with BK5 ≥ 30%.

---

### BK5 — Salesperson Adoption

**Data source:** `feedback_record` joined to `pipeline_run`.

```sql
SELECT
  COUNT(DISTINCT pr.id) FILTER (WHERE fr.id IS NOT NULL) AS leads_with_feedback,
  COUNT(DISTINCT pr.id) AS total_delivered,
  COUNT(DISTINCT pr.id) FILTER (WHERE fr.id IS NOT NULL)::float / NULLIF(COUNT(DISTINCT pr.id), 0) AS adoption_rate
FROM pipeline_run pr
LEFT JOIN feedback_record fr ON fr.pipeline_run_id = pr.id
WHERE pr.tenant_id = $tenant_id
  AND pr.status = 'delivered'
  AND pr.created_at >= NOW() - INTERVAL '14 days';
```

**Why 30% is the floor:** The feedback loop (documented in [[analyses/governance-observability-layer]]) needs sufficient signal to generate pattern detection insights for team lead review. Below 30%, the pattern detector lacks statistical confidence. Above 30%, feedback-driven re-runs of Pipeline 2 become meaningful.

**Note:** The 30% threshold is also one of the MVP Business Conditions in [[analyses/mvp-scope-sign-off]] §4.

**If adoption is low:** The team lead is the escalation point. Common causes: salesperson doesn't know feedback exists (UX issue), or salesperson doesn't trust the scores (scoring quality issue → check BK4).

---

### BK6 — Cost per Converted Lead

**Calculation:**
```
cost_per_converted_lead = total_monthly_system_cost / total_confirmed_conversions_this_month
```

**Total monthly system cost** = LLM API fees + enrichment API fees + infrastructure costs.

**Why this matters:** At 3 tenants and low volume, the absolute cost is low. This metric is tracked now so that a baseline is established before scaling. Post-MVP, if cost per converted lead increases despite lower cost per lead (OP6), it means scoring quality is degrading — more leads are being processed but fewer converting.

**Note:** Infrastructure costs are TBD until tech stack is locked during build. Track LLM + enrichment costs from Day 1; add infrastructure costs once monthly bills are available.

---

## 4. Data Sources and Write Points

| Metric | Primary Source | Write Point |
|---|---|---|
| OP1, OP3 | `quality_snapshots` | After each Pipeline 1 run |
| OP2 | `task_execution.duration_ms` (stage=score) | Score stage completion |
| OP4 | `enrichment_quota` + `task_execution` | Per enrichment call |
| OP5 | `task_execution` (background job events) | Job start + completion |
| OP6 | `task_execution.metadata.token_usage` + monthly invoice | Score stage + monthly job |
| OP7 | Workflow engine queue | Real-time (implementation TBD) |
| BK1 | `tenant.status` | Pipeline 2 completion + readiness check |
| BK2 | `feedback_record` + `pipeline_run` | On first conversion feedback |
| BK3, BK4, BK5, BK6 | `feedback_record` + `pipeline_run` | On feedback submission |

**Rule:** All dashboard panels that show quality or business metrics **must read from `quality_snapshots`**, not from `pipeline_run` directly. This is the read model rule established in [[analyses/service-scaling-strategy]] and enforced by [[analyses/devops-controls]].

---

## 5. Review Cadence

| Layer | Cadence | Who |
|---|---|---|
| Operational KPIs (OP1–OP7) | Real-time on Ops Dashboard | Engineering lead |
| Scoring Quality KPIs (AP/C/AR) | Weekly quality snapshot | Team lead |
| Business KPIs (BK1–BK6) | Monthly tenant quality report | Admin, product, team leads |

**Exception:** BK5 (Salesperson Adoption) is also surfaced weekly on the Tenant Quality Dashboard, as it is an early warning signal for feedback loop health.

---

## 6. Connection to MVP Sign-Off

From [[analyses/mvp-scope-sign-off]] §4, the sign-off conditions that map to these KPIs:

| Sign-Off Condition | KPI | Target |
|---|---|---|
| Pipeline coverage ≥ 80% of leads reach delivered or human_review | OP3 (also quality_snapshots System Health row) | OP3 ≥ 98%; sign-off threshold ≥ 80% |
| Zero scoring failures < 2% | OP3 inverse | failed_rate < 2% |
| HOT SLA compliance ≥ 80% HOT leads contacted within 24h | AR1 (from [[analyses/action-relevance-metrics]]) | Operational prerequisite: OP5 (sla_breach_check job must be running) |
| Scoring Lift > 1.5 | BK4 (= AP2) | > 1.5 |
| Salesperson feedback rate ≥ 30% | BK5 | ≥ 30% |
| At least 1 HOT lead converted per tenant | BK3 | ≥ 1 conversion per tenant |

All sign-off conditions require 2 consecutive weeks of data. Operational KPIs (OP1–OP7) must be stable before the 2-week clock starts — a system that is crashing cannot accumulate valid business metric data.

---

## Confirmed Decisions

| Decision | Basis |
|---|---|
| Operational KPIs read from quality_snapshots (not raw pipeline_run) | [[analyses/service-scaling-strategy]] + [[analyses/devops-controls]] |
| Cost per Lead target < $0.05 | [[analyses/lead-enrichment-architecture]] cost model + [[analyses/tech-stack-research]] LLM estimate |
| Salesperson Adoption ≥ 30% is a prerequisite for BK3/BK4 reliability | [[analyses/governance-observability-layer]] feedback loop design |
| BK4 (Scoring Lift) = AP2 (Discrimination Ratio) — same metric, different audience | [[analyses/accuracy-proxy-metrics]] |
| Infrastructure costs tracked starting from build (not estimated in advance) | Tech stack TBD during build; see [[analyses/observability-detail-spec]] Open Decisions |
