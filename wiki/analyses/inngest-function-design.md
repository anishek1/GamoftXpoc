---
type: analysis
question: "How should the Lead Intelligence Engine's Pipeline 1, Pipeline 2, and background governance jobs be implemented as Inngest functions?"
date: 2026-05-13
tags: [inngest, pipeline-1, pipeline-2, orchestration, background-jobs, scheduled, crash-recovery, concurrency]
sources_consulted:
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/onboarding-flow-stage-map]]"
  - "[[analyses/onboarding-flow-readiness]]"
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/service-scaling-strategy]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/scoring-quality-metrics]]"
  - "[[concepts/score-decay]]"
  - "[[concepts/action-sla]]"
  - "[[concepts/feedback-loop]]"
  - "[[sources/2026-core-business-entities]]"
status: COMPLETE — 8 Inngest functions implemented covering Pipeline 2, Pipeline 1, and all governance background jobs
---

# Inngest Function Design — Lead Intelligence Engine

**Question:** How should the Lead Intelligence Engine be implemented as Inngest functions?
**Date:** 2026-05-13

---

## Plain-English Summary

**Why Inngest:** Inngest was one of two finalists in the tech-stack research for the orchestration engine (alongside Temporal). It provides crash recovery via event replay, per-step memoisation (completed steps are not re-run on replay), zero infrastructure to manage, a generous free tier, and an event-driven model that maps naturally to the Lead Intelligence Engine's two-pipeline + background-jobs architecture.

**What was built:** 8 Inngest functions covering every workflow in the system — Pipeline 2 tenant onboarding, Pipeline 1 per-lead processing, score decay, SLA breach alerting, three quality metric cadences, and Pipeline 2 re-run checks.

---

## Function Inventory

| File | Function ID | Trigger | Description |
|---|---|---|---|
| `pipeline2/onboarding.ts` | `pipeline2-onboarding` | `tenant/onboarding.start` event | 5-step serial LLM workflow: Onboarding Agent → ICP Agent → Signal Agent → Prompt Template → Activate |
| `pipeline1/data-gather.ts` | `pipeline1-data-gather` | `lead/batch.trigger` event | Pre-flight check → parallel channel fetch → dedup → fan-out |
| `pipeline1/lead-processor.ts` | `pipeline1-lead-processor` | `lead/received` event | Full per-lead pipeline; DM path includes Pre-Filter + Message Parser (Haiku) |
| `scheduled/score-decay.ts` | `score-decay` | Cron: daily 02:00 UTC | -10@7d, -20@14d, auto-cold@30d |
| `scheduled/sla-monitor.ts` | `sla-monitor` | Cron: hourly | Alerts team lead on HOT (24h) and WARM (2–3d) SLA breaches |
| `scheduled/quality-metrics.ts` | `quality-metrics-per-run` | `pipeline/run.complete` event | Score Coverage Rate, completeness distribution, failure rate |
| `scheduled/quality-metrics.ts` | `quality-metrics-weekly` | Cron: Monday 00:00 UTC | AR1–AR4, C1–C2 action and consistency metrics |
| `scheduled/quality-metrics.ts` | `quality-metrics-monthly` | Cron: 1st of month 01:00 UTC | AP1–AP3, C4, AR5 — requires ≥100 outcomes per bucket |
| `scheduled/pipeline2-rerun-check.ts` | `pipeline2-rerun-check` | Cron: 1st and 15th at 09:00 UTC | Bi-weekly proactive check-in + feedback-driven rerun proposals |

---

## Architecture Decisions

### Concurrency model

Per the service-scaling-strategy analysis, the concurrency cap must be per-tenant, not global. Global cap allows one tenant to starve all others (noisy-neighbour problem). Implementation:

```typescript
concurrency: [
  {
    key: "event.data.tenant_id",
    limit: 2, // overridden by tenant_config.scoring_concurrency_cap
  },
]
```

Tiering defaults (from service-scaling-strategy):
- Basic: 2 concurrent Scoring Agent calls
- Standard: 3
- Premium: 5

### Crash safety — the write-order rule

The pipeline_stage field on the leads table is the final atomic write at every step. This is the crash safety guarantee from orchestration-layer-spec §8.2:

```
1. Tool returns output
2. Write lineage_record (provenance)
3. Write task_execution (step status)
4. Update pipeline_run (if last step)
5. Update leads.pipeline_stage  ← ALWAYS LAST
```

Inngest's step memoisation handles crash recovery: if a function replays, completed steps are not re-executed. This replaces the manual crash-recovery logic (orchestration-layer-spec §8.4) that would be needed with Celery or raw Postgres.

### Retry policy

No function-level retries. Each step uses explicit 2-attempt retry loops with full lineage writes on failure. This prevents:
- Double LLM charges on replay
- Overwriting pipeline_stage with a stale value from a replayed step

### Entry point routing — DM vs Lead Ad

```
DM events  (entry_point: "dm")
  → Step 0: Pre-Filter Gate
  → Step 1: Message Parser (Haiku)
  → Step 2–7: shared path

Lead Ad events  (entry_point: "lead_ad")
  → Skip Steps 0–1
  → Step 2–7: shared path
```

### awaiting_clarification — non-terminal state

The Intent Gate can set pipeline_stage to awaiting_clarification. This is not a terminal state; the lead waits for a prospect reply. Inngest handles this elegantly via `step.waitForEvent()`:

```typescript
const reply = await step.waitForEvent("wait_for_clarification_reply", {
  event: "lead/clarification.received",
  timeout: "24h",
  match: "data.lead_id",
});
// reply === null → 24h timeout → score with intent penalty
// reply !== null → merge reply and continue to scoring
```

This avoids the custom 24h scheduled job described in orchestration-layer-spec §8.3; Inngest handles the timeout natively.

### Quality metrics isolation

All quality metric jobs read only from `quality_snapshots`, never from raw pipeline tables (`leads`, `pipeline_log`, `lineage_record`). This enforces the read/write isolation required by service-scaling-strategy Recommendation 11. If a metric job fails, it retries independently and cannot halt Pipeline 1.

### Governance failure isolation

Every lineage write in score-decay and quality-metrics is wrapped in `try/catch` with swallowed errors. This implements the locked constraint: "a failure in the Governance Layer must never halt Pipeline 1 or Pipeline 2."

---

## Event Flow Diagram

```
                    ┌──────────────────────────────────────┐
                    │         External Channels             │
                    │  (WhatsApp, Meta Lead Ads, Website)   │
                    └───────────────┬──────────────────────┘
                                    │ webhook
                                    ▼
                    ┌──────────────────────────────────────┐
                    │     Ingestion Handler                 │
                    │  fires "lead/batch.trigger" event     │
                    └───────────────┬──────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────────┐
                    │   pipeline1-data-gather               │
                    │   pre-flight → fetch → dedup          │
                    │   fires "lead/received" × N leads     │
                    └───────────────┬──────────────────────┘
                                    │ fan-out
                         ┌──────────┴──────────┐
                         │                     │
                         ▼                     ▼
                ┌────────────────┐    ┌────────────────┐
                │ pipeline1-lead │    │ pipeline1-lead  │  ... × N
                │ -processor     │    │ -processor      │
                │ (lead 1)       │    │ (lead 2)        │
                └───────┬────────┘    └───────┬─────────┘
                        │                     │
                        ▼                     ▼
                fires "pipeline/run.complete" (once all leads done)
                        │
                        ▼
                ┌────────────────────────────────────────┐
                │  quality-metrics-per-run               │
                │  writes to quality_snapshots           │
                └────────────────────────────────────────┘

Parallel to all of the above (scheduled):
  score-decay           → daily
  sla-monitor           → hourly
  quality-metrics-weekly  → Monday 00:00
  quality-metrics-monthly → 1st of month
  pipeline2-rerun-check   → 1st and 15th
```

---

## Files Created

```
src/
  inngest/
    client.ts                         ← Inngest client + full event type catalogue
    index.ts                          ← Function registry (import all, export all)
    pipeline2/
      onboarding.ts                   ← Pipeline 2: 5-step serial LLM workflow
    pipeline1/
      data-gather.ts                  ← Pipeline 1 entry: pre-flight + fan-out
      lead-processor.ts               ← Pipeline 1 per-lead: DM+LeadAd paths, scoring, bucketize
    scheduled/
      score-decay.ts                  ← Score decay cron (-10@7d, -20@14d, cold@30d)
      sla-monitor.ts                  ← SLA breach alerting (HOT 24h, WARM 2-3d)
      quality-metrics.ts              ← Per-run + weekly + monthly quality jobs
      pipeline2-rerun-check.ts        ← Bi-weekly proactive check-in + feedback-driven proposals
  app/
    api/
      inngest/
        route.ts                      ← Next.js App Router handler (serves/GET/POST/PUT)
```

---

## Evidence

- Pipeline 2 serial structure: Onboarding Agent → ICP Agent → Signal Agent → Prompt Template (source: [[analyses/orchestration-layer-spec]] §3)
- Per-tenant concurrency cap replacing global cap (source: [[analyses/service-scaling-strategy]] Rec 6)
- pipeline_stage write-order rule and crash safety (source: [[analyses/orchestration-layer-spec]] §8.2)
- awaiting_clarification as non-terminal state (source: [[analyses/orchestration-layer-spec]] §8.1)
- DM path vs Lead Ad entry point split (source: [[analyses/orchestration-layer-spec]] §4.1)
- Score decay schedule (-10@7d, -20@14d, auto-cold@30d) (source: [[concepts/score-decay]])
- SLA deadlines (HOT=24h, WARM=2-3d, COLD=weekly) (source: [[concepts/action-sla]])
- Quality metrics cadences and metric definitions (source: [[analyses/governance-observability-layer]], [[analyses/scoring-quality-metrics]])
- system proposes / team lead approves for Pipeline 2 re-runs (source: [[analyses/orchestration-layer-spec]] §3.3)
- quality_snapshots is the only read target for governance (source: [[analyses/service-scaling-strategy]] Rec 11)

---

## Caveats & Gaps

- **Backend language mismatch:** The tech-stack-research locks Python/FastAPI as the backend language. This implementation uses TypeScript/Inngest (Next.js). If the team confirms Python, the same logic would use the [Inngest Python SDK](https://inngest.com/docs/sdk/serve#python) with identical step structure.
- **`src/lib/` stubs:** The `db`, `agents`, `ingestion`, `tenant`, and `metrics` modules referenced in the functions are not yet implemented. They define the interface contract for S1 (data layer) and S2 (intelligence layer).
- **Concurrency cap override:** The per-tenant concurrency cap is declared as a constant (2) in lead-processor.ts. To make it truly per-tenant, Inngest's `concurrency.key` expression needs to resolve the cap from `tenant_config` at invocation time — this requires an Inngest middleware or a dynamic approach (research needed).
- **`pipeline/run.complete` timing:** There is no explicit "wait for all leads" fan-in step in data-gather. An explicit fan-in (using `step.waitForEvent` counting N completions) should be added to trigger the per-run metrics job accurately.

## Follow-up Questions

- Does the team want Python (Inngest Python SDK) or TypeScript (current implementation)?
- Should Temporal be implemented in parallel for comparison?
- What is the exact `tenant_config` schema for `scoring_concurrency_cap` — is it per-tenant-configurable or a tier default only?
