---
type: overview
last_updated: 2026-04-19
source_count: 1
---

# Knowledge Base Overview

**Last updated:** 2026-04-19 | **Sources ingested:** 1

## What This Wiki Is About

Pre-planning and architecture documentation for the **Multi-Tenant Adaptive Lead Intelligence Engine** — a production-grade agentic pipeline being built by [[entities/gamoft]] (owner: [[entities/anishekh]]) to score and prioritize sales leads for three POC tenants: [[entities/gamoft]] (B2B), [[entities/urvee-organics]] (B2C), and [[entities/govmen]] (TBD).

## Current Thesis / Best Understanding

The system runs **two pipelines** from one orchestrator. Pipeline 2 (Onboarding) runs once per tenant to produce intelligence configuration: a business persona, an ideal customer profile, and a set of signal definitions. Pipeline 1 (Event/Lead) runs per lead — it gathers data, extracts signal values deterministically, and passes them to the Scoring Agent via a fill-in-the-blanks prompt template. The Scoring Agent is the only LLM call per lead, keeping per-lead cost predictable.

The product vision is unchanged: **salespeople never leave the chat interface.** They ask natural questions, get ranked lead cards with scores, confidence levels, and plain-language explanations. All agents, signals, and schemas are invisible to the user.

**What's locked:** The 5 design principles, the two-pipeline architecture, 4 LLM agents (Onboarding, ICP, Signal, Scoring), deterministic signal extraction, fill-in-the-blanks prompt mechanism, bucket thresholds (80/55/0 — starting points), 5 Add-ons, Postgres state store, serial build order.

**What's changed from original source doc:** Pipeline count (1 → 2), LLM agent count (1 → 4), bucket thresholds (75/45 → 80/55), pipeline stage names updated, Governance Layer added as explicit cross-cutting layer.

**What's deferred:** The Adaptive Signal Lifecycle (Add-ons 6/7/8) — requires 2-3 months of real production data.

**What's TBD:** ~50+ open decisions in Section 16 of source doc, plus new items: signal detection_rule format, Pipeline 2 re-run triggers, prompt template versioning, onboarding/ICP/signal agent output schemas.

## Major Themes

- **[[concepts/lead-pipeline-architecture]]** — two-pipeline architecture; Pipeline 2 one-time setup, Pipeline 1 per-lead
- **[[concepts/agent-vs-tool-classification]]** — 4 LLM agents (3 in Pipeline 2, 1 in Pipeline 1); 1 LLM call per lead preserved
- **[[concepts/persona-layer]]** — per-tenant rich business profile; produced by Onboarding Agent in Pipeline 2
- **[[concepts/confidence-first-class]]** — confidence as user-visible field; routing logic at 3 bands; calculation TBD
- **[[concepts/lineage-log]]** — non-negotiable audit trail; written by orchestrator at every stage, both pipelines
- **[[concepts/disqualification-gate]]** — score gates before bucketing; prevents wrong leads reaching HOT
- **[[concepts/score-decay]]** + **[[concepts/action-sla]]** — temporal enforcement; SLA breach → alert
- **[[concepts/capability-registry]]** — drives Pipeline 1 tool sequence; zero orchestrator changes per new use case
- **[[concepts/adaptive-signal-lifecycle]]** — deferred to Sprint 2-3; needs real production data

## Key Entities

- [[entities/gamoft]] — builder and B2B self-tenant; AWS likely; tech stack TBD
- [[entities/urvee-organics]] — B2C tenant; Instagram + WhatsApp; persona TBD
- [[entities/govmen]] — third tenant; everything TBD
- [[entities/anishekh]] — project lead and document owner

## Open Questions

1. **Signal detection_rule format:** How are signal values extracted deterministically? What evaluation engine? `[TBD from S2]`
2. **Pipeline 2 re-run triggers:** When does onboarding re-run? Tenant business change? Manual trigger? `[TBD — team decision]`
3. **Confidence calculation method:** Still unresolved — see [[analyses/confidence-scoring-brainstorm]]
4. **Technology stack:** Backend language, LLM provider, secrets vault, observability tooling — all `[TBD]`
5. **Tenant personas:** All three personas `[TBD]` — Govmen profile entirely unknown
6. **Scoring weights per tenant:** Playbook gives illustrative weights (Fit 25%, Intent 30%, Engagement 20%, Behavioral 15%, Context 10%); need tenant-specific values
7. **Bucket threshold calibration:** 80/55/0 confirmed as starting points; calibrate after Month 1 data
8. **~50 additional TBDs** in Section 16 of [[sources/2026-lead-intelligence-engine-reference]]

## What to Read Next

- Define signal detection_rule format with S2 team — blocks orchestrator's lead enrichment logic
- Define Gamoft B2B persona (easiest — self-knowledge) to pilot Pipeline 2
- Research LLM provider costs — now need to account for 4 LLM agents, not 1
- LinkedIn API compliance decision — blocks lead enrichment (public web step)
- Govmen discovery session — tenant is entirely undefined
