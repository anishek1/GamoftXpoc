---
type: concept
name: "Lead Pipeline Architecture"
aliases: ["two-pipeline architecture", "event pipeline", "onboarding pipeline"]
tags: [pipeline, architecture, agentic, multi-tenant, two-pipeline]
source_count: 1
last_updated: 2026-04-19
---

# Lead Pipeline Architecture

## Definition

The system runs **two distinct pipelines**, both originating from the orchestrator. Pipeline 2 (Onboarding) runs once per tenant at setup. Pipeline 1 (Event/Lead) runs per lead event. Together they produce scored, bucketed leads delivered to the user in the chat interface.

## Two-Pipeline Overview

```
                    ┌─────────────────┐
                    │   ORCHESTRATOR   │
                    └────────┬────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                      │
          ▼                                      ▼
PIPELINE 2 — ONBOARDING               PIPELINE 1 — EVENT/LEAD
(one-time per tenant)                 (per lead, per event)
Onboarding Agent (LLM)                Event trigger
ICP Agent (LLM)                       Data Gather
Signal Agent (LLM)                    Lead Enrichment
       │                              Normalise
       │ signal definitions           Scoring Agent (LLM)
       └─────────────────────────────►Bucketize
                                           │
                    ┌──────────────────────┘
                    ▼
          GOVERNANCE LAYER
 monitoring · lineage · feedback
 quality tracking · security
```

## Pipeline 2 — Onboarding

Runs once when a tenant is onboarded. Re-runs when tenant business profile changes.

| Stage | Agent | Output |
|---|---|---|
| 1 | Onboarding Agent (LLM) | Business persona object |
| 2 | ICP Agent (LLM) | Ideal customer profile definition |
| 3 | Signal Agent (LLM) | Signal definitions per scoring dimension |
| — | System | Prompt template generated using signal slots |

The Signal Agent decides how many signals are needed per dimension (Intent: 5+, Engagement: 6+, others TBD). Signal definitions become the fill-in-the-blank slots in the Scoring Agent's prompt template.

## Pipeline 1 — Event/Lead Flow

| Stage | Type | Output |
|---|---|---|
| Event trigger | TOOL | Structured task / run_id |
| Data Gather | TOOL | Raw leads from all channels |
| Lead Enrichment | TOOL (deterministic) | Enriched lead + extracted signal values |
| Normalise | TOOL | Clean unified lead schema |
| Scoring Agent | LLM AGENT | Score, bucket, explanation, confidence |
| Bucketize | TOOL | HOT / WARM / COLD + SLA |

## Lead Status Transitions (Pipeline 1)

```
captured
  → fetched
    → enriched
      → normalised
        → scored
          → delivered
          → human_review   (confidence < 50% or scoring_failed)

[any non-terminal] → failed
```

## LLM Agents — Full List

**Total: 4 LLM agents** (significant change from original 1-agent principle — Pipeline 2 agents are one-time setup, not per-lead)

| Agent | Pipeline | Frequency |
|---|---|---|
| Onboarding Agent | Pipeline 2 | Once per tenant onboarding |
| ICP Agent | Pipeline 2 | Once per tenant onboarding |
| Signal Agent | Pipeline 2 | Once per tenant onboarding |
| Scoring Agent | Pipeline 1 | Once per lead |

## Bucket Thresholds `[CONFIRMED — playbook v1.0, tenant-configurable]`

| Bucket | Score | SLA |
|---|---|---|
| HOT | 80–100 | 24 hours |
| WARM | 55–79 | 2–3 days |
| COLD | 0–54 | Weekly nurture |

Thresholds are starting points. Calibrate after Month 1 using AP1 and AP2 scoring quality metrics.

## Governance Layer

Cross-cutting, not part of either pipeline's sequential flow. Covers: monitoring, auditability, lineage, feedback loops, quality tracking, security controls.

## Build Order `[LOCKED — from source ref, updated for two-pipeline]`

1. Lead schema + state store (Postgres tables)
2. Personas + signal_definitions tables
3. Pipeline 2: Onboarding Agent skeleton (mock outputs)
4. Pipeline 1: Orchestrator skeleton with mock agent responses
5. Agent A — data gather (one source only: website first)
6. Lead Enrichment — deterministic signal extraction
7. Normalise
8. Observability + lineage logging layer
9. Scoring Agent — first end-to-end Pipeline 1 test
10. ICP Agent + Signal Agent (Pipeline 2 complete)
11. Disqualification + Decay + SLA rules
12. Feedback loop v1
13. Add WhatsApp, Facebook, Instagram to Data Gather
14. Multi-tenant expansion

## Why It Matters

The two-pipeline separation means:
- Onboarding intelligence (what signals matter for this tenant) is defined ONCE by LLM, not recalculated per lead
- Per-lead scoring uses one LLM call only (Scoring Agent) — cost stays predictable
- Signal definitions are explicit and stored — debuggable, versionable, auditable

## Tensions & Contradictions

- Original source doc stated "1 LLM agent in the entire pipeline" `[LOCKED]`. The team has since decided on 4 LLM agents. Pipeline 2 agents are one-time setup (not per-lead), so per-lead cost principle is preserved. The original principle should be updated to: "1 LLM agent per lead in Pipeline 1; Pipeline 2 agents are one-time setup."

## Related Concepts

- [[concepts/agent-vs-tool-classification]] — updated classification for 4 LLM agents
- [[concepts/persona-layer]] — produced by Onboarding Agent in Pipeline 2
- [[concepts/confidence-first-class]] — output of Scoring Agent, drives routing
- [[concepts/lineage-log]] — written at every stage, both pipelines
- [[concepts/disqualification-gate]] — applied in Pipeline 1 before bucketing
- [[concepts/score-decay]] — background job after Pipeline 1
- [[concepts/action-sla]] — assigned at Bucketize stage
- [[concepts/capability-registry]] — drives Pipeline 1 tool sequence
- [[concepts/feedback-loop]] — feeds Governance Layer

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 01, 03, 12, 14, 19
- raw/assets/lead_intelligence_manual_enrichment_playbook — enrichment dimensions, bucket thresholds, governance rules
