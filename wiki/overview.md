---
type: overview
last_updated: 2026-04-22
source_count: 3
---

# Knowledge Base Overview

**Last updated:** 2026-04-22 | **Sources ingested:** 3

## What This Wiki Is About

Pre-planning and architecture documentation for the **Multi-Tenant Adaptive Lead Intelligence Engine** — a production-grade agentic pipeline being built by [[entities/gamoft]] (owner: [[entities/anishekh]]) to score and prioritize sales leads for three POC tenants: [[entities/gamoft]] (B2B), [[entities/urvee-organics]] (B2C), and [[entities/govmen]] (TBD).

## Current Thesis / Best Understanding

The system runs **two pipelines** from one orchestrator. Pipeline 2 (Onboarding) runs once per tenant to produce intelligence configuration: a business persona, an ideal customer profile, and a set of signal definitions. Pipeline 1 (Event/Lead) runs per lead — it gathers data, extracts signal values deterministically, and passes them to the Scoring Agent via a fill-in-the-blanks prompt template. The Scoring Agent is the only LLM call per lead, keeping per-lead cost predictable.

The product vision is unchanged: **salespeople never leave the chat interface.** They ask natural questions, get ranked lead cards with scores, confidence levels, and plain-language explanations. All agents, signals, and schemas are invisible to the user.

**The measurement system is now fully documented and connected to the execution system.** The orchestrator writes lineage after every stage of every lead. Scheduled SQL jobs read that lineage to compute quality metrics at three cadences (per-run, weekly, monthly). Results flow into three Global KPIs (System Health, Business Health, Tenant Health Rate). Team lead and product owner reviews close the loop back to the orchestrator — recalibrating bucket thresholds, signal weights, or triggering Pipeline 2 re-runs. The full lifecycle is diagrammed in [[analyses/orchestration-layer-spec]] Section 5.1.

**What's locked:** The 5 design principles, the two-pipeline architecture, 4 LLM agents (Onboarding, ICP, Signal, Scoring), deterministic signal extraction, fill-in-the-blanks prompt mechanism, bucket thresholds (80/55/0 — starting points), 5 Add-ons, Postgres state store, serial build order, governance layer failure must not halt pipelines, system proposes / human approves on all config changes. The Intelligence Layer's four-component internal design (Persona Engine → Prompt Layer → Rating Agent → Output Schema Layer) and its `score_lead()` interface are now specified. The full data entity catalog (32 entities across 3 groups) is now documented. The five scoring dimensions (Fit 25%, Intent 25%, Engagement 20%, Behaviour 20%, Context 10%) and their default weights are locked.

**What's changed from original source doc:** Pipeline count (1 → 2), LLM agent count (1 → 4), bucket thresholds (75/45 → 80/55), pipeline stage names updated, Governance Layer added as explicit cross-cutting layer, quality metrics fully wired to orchestration layer. **Correction (2026-04-22):** The "confidence" field in the intelligence layer design is a **lead completeness score**, not LLM self-assessed confidence. LLMs are poorly calibrated; the field measures completeness of enriched lead data instead. Routing logic and `needs_review` flag are unchanged.

**What's deferred:** The Adaptive Signal Lifecycle (Add-ons 6/7/8) — requires 2-3 months of real production data.

**What's TBD:** ~50+ open decisions in Section 16 of source doc, plus: signal detection_rule format, Pipeline 2 re-run triggers, prompt template versioning, onboarding/ICP/signal agent output schemas, Scoring Agent concurrency cap (recommend 5), concurrency guard timeout threshold (recommend 15–30 min), alert thresholds for monitoring (all after Month 1 baseline), secrets vault choice (AWS vs HashiCorp), auth library, observability tooling.

## Major Themes

- **[[concepts/lead-pipeline-architecture]]** — two-pipeline architecture; Pipeline 2 one-time setup, Pipeline 1 per-lead; pipeline output feeds the quality metrics layer
- **[[concepts/intelligence-layer]]** — four-component internal pipeline (Persona Engine → Prompt Layer → Rating Agent → Output Schema Layer); single `score_lead()` entry point; 60-second hard timeout; never writes to data layer directly
- **[[concepts/signal-types]]** — five scoring dimensions (Fit 25%, Intent 25%, Engagement 20%, Behaviour 20%, Context 10%); defaults overridden per tenant via persona; both data model (`signal`, `signal_evaluation`) and prompt structure
- **[[concepts/data-entity-model]]** — 32 entities in 3 groups: core lead lifecycle (15), governance & quality (6), operational observability & delivery (11)
- **[[concepts/agent-vs-tool-classification]]** — 4 LLM agents (3 in Pipeline 2, 1 in Pipeline 1); 1 LLM call per lead preserved
- **[[concepts/persona-layer]]** — per-tenant rich business profile; produced by Onboarding Agent in Pipeline 2; built and cached by Persona Engine (first component of intelligence layer); versioning confirmed
- **[[concepts/confidence-first-class]]** — **corrected 2026-04-22**: this is a lead completeness score, not LLM confidence; routing and `needs_review` flag unchanged; threshold `[TBD]`
- **[[concepts/lineage-log]]** — non-negotiable audit trail; written by orchestrator at every stage, both pipelines; primary data source for all scoring quality metrics; backed by `lineage_record` entity
- **[[concepts/disqualification-gate]]** — score gates before bucketing; prevents wrong leads reaching HOT
- **[[concepts/score-decay]]** + **[[concepts/action-sla]]** — temporal enforcement; SLA breach → alert; decay coherence tracked via C4 metric
- **[[concepts/capability-registry]]** — drives Pipeline 1 tool sequence; zero orchestrator changes per new use case
- **[[concepts/feedback-loop]]** — 3-step enforcement (attribution → pattern detection → team lead recommendation); backed by `feedback_record` entity
- **[[concepts/adaptive-signal-lifecycle]]** — deferred to Sprint 2-3; needs real production data

## Key Analyses — Documentation State

| Document | State | What it covers |
|---|---|---|
| [[analyses/orchestration-layer-spec]] | COMPLETE | Two-pipeline architecture, controller, tool invocation, state tracking; updated system architecture diagram with KPI layer; Section 5.1 KPI orchestration workflow |
| [[analyses/governance-observability-layer]] | COMPLETE | All 6 domains with correct section ordering and numbering; full how/why reasoning throughout; 3-step feedback loop; 3-layer security |
| [[analyses/scoring-quality-metrics]] | COMPLETE | Score Coverage + Accuracy Proxy (AP1–AP3) + Consistency (C1–C5) + Action Relevance (AR1–AR5) + 3 Global KPIs; now cross-referenced from both other docs |
| [[analyses/orchestration-layer-dependencies]] | COMPLETE | 3 hard blockers (S1: pipeline_stage values + pipeline_log schema; S2: Scoring Agent output schema) |
| [[analyses/confidence-scoring-brainstorm]] | IN PROGRESS | Now tracking lead completeness score (not LLM confidence); formula and threshold still unresolved |
| [[sources/2026-intelligence-layer-design]] | INGESTED 2026-04-22 | Intelligence Layer design spec: 4-component pipeline, score_lead() interface, 5 scoring dimensions, open decisions |
| [[sources/2026-core-business-entities]] | INGESTED 2026-04-22 | Full data entity catalog: 32 entities across lead lifecycle, governance, and operational observability |

## Key Entities

- [[entities/gamoft]] — builder and B2B self-tenant; AWS likely; tech stack TBD
- [[entities/urvee-organics]] — B2C tenant; Instagram + WhatsApp; persona TBD; consent_preference entity especially relevant for their channels
- [[entities/govmen]] — third tenant; everything TBD
- [[entities/anishekh]] — project lead and document owner

## Open Questions

1. **Signal detection_rule format:** How are signal values extracted deterministically? What evaluation engine? `[TBD from S2]` — hard blocker for orchestrator Lead Enrichment stage. Now also a hard blocker for the `signal` entity schema in the data model.
2. **Pipeline 2 re-run triggers:** Proactive check-in cadence (2-week or monthly?) and feedback-driven flagging threshold (fixed count N = ?) `[TBD — team decision after Month 1]`
3. **Lead completeness score formula and threshold:** Confirmed it's completeness (not LLM confidence) — see [[analyses/confidence-scoring-brainstorm]]; formula and `needs_review` threshold `[TBD]`
4. **Technology stack:** Backend language, LLM provider (Groq vs OpenAI — open decision in intelligence layer spec), model config scope (global vs per-tenant), prompt storage (code vs data layer), secrets vault (AWS vs HashiCorp), observability tooling — all `[TBD]`
5. **Tenant personas:** All three personas `[TBD]` — Govmen profile entirely unknown; Urvee-Organics and Gamoft need signal weight configuration
6. **Scoring Agent concurrency cap:** Recommend 5 — needs team decision based on LLM provider rate limits
7. **Concurrency guard timeout threshold:** Recommend 15–30 min — needs team decision balancing false recovery vs slow recovery
8. **Alert thresholds:** All monitoring and quality alert thresholds `[TBD — set after Month 1 baseline]`
9. **Bucket threshold calibration:** 80/55/0 confirmed as starting points; AP1 and AP2 drive recalibration after Month 1
10. **S1/S2 hard blockers:** `leads.pipeline_stage` accepted values (S1), `pipeline_log` schema (S1), Scoring Agent output JSON schema incl. confidence field format (S2)
11. **~50 additional TBDs** in Section 16 of [[sources/2026-lead-intelligence-engine-reference]]

11. **Intelligence layer open decisions:** Primary LLM provider, model config scope, prompt storage location, custom rules format (free-text vs structured pre-LLM execution), bucket disagreement handling — 6 open decisions from [[sources/2026-intelligence-layer-design]] Section 7.
12. **Data entity open questions:** `signal` entity schema (detection_rule format); `quality_rule` storage format; relationship between `report_definition` and `dashboard_definition`; `alert_incident` creation trigger.

## What to Read Next

- **Immediate:** Define `signal detection_rule` format with S2 — this is a hard blocker; no lead enrichment code can be written without it
- **Immediate:** Lock `leads.pipeline_stage` accepted string values with S1 — orchestrator reads and writes this field at every stage
- **Immediate:** Lock `pipeline_log` schema with S1 — lineage must be built before the second LLM agent is added
- **Next sprint:** Define Gamoft B2B persona and run Pipeline 2 end-to-end — easiest tenant (self-knowledge) and the only way to validate the onboarding flow
- **Next sprint:** Set WARM SLA window (48h or 72h) — blocks AR1 SLA Compliance metric calculation
- **Before Month 1:** Research LLM provider costs for 4 agents; LinkedIn API compliance decision for lead enrichment
- **Month 1 unlock:** Set all monitoring alert thresholds; set Tenant Health Rate thresholds; recalibrate bucket boundaries using AP1/AP2; set flagging threshold N for pattern detection
