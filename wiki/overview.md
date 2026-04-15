---
type: overview
last_updated: 2026-04-14
source_count: 1
---

# Knowledge Base Overview

**Last updated:** 2026-04-14 | **Sources ingested:** 1

## What This Wiki Is About

Pre-planning and architecture documentation for the **Multi-Tenant Adaptive Lead Intelligence Engine** — a production-grade agentic pipeline being built by [[entities/gamoft]] (owner: [[entities/anishekh]]) to score and prioritize sales leads for three POC tenants: [[entities/gamoft]] (B2B), [[entities/urvee-organics]] (B2C), and [[entities/govmen]] (TBD).

## Current Thesis / Best Understanding

The system's architectural bet is: **minimize LLM usage to one holistic judgment per lead** (Agent E), make everything else deterministic tooling, and use a rich per-tenant [[concepts/persona-layer]] as the source of competitive differentiation. The result is a scoring system that is affordable to run at scale, predictable to debug, and produces tenant-aware scores that a generic CRM cannot replicate.

The product vision is: **salespeople never leave the chat interface.** They ask natural questions ("who should I call today"), get ranked lead cards with scores, confidence levels, and plain-language explanations. All agents, signals, and schemas are invisible.

**What's locked:** The 5 design principles, the 22-component pipeline architecture, 5 core Add-ons (agent/tool classification, persona layer, confidence-first-class, disqualification+decay+SLA, Postgres state store), and the serial build order.

**What's deferred:** The Adaptive Signal Lifecycle (Add-ons 6/7/8) — requires 2-3 months of real production data before it can measure anything meaningful.

**What's TBD:** ~50+ open decisions tracked in Section 16 of the source document, including technology stack, all three tenant personas, all DB schemas, and the full disqualification rule set.

## Major Themes

- **[[concepts/lead-pipeline-architecture]]** — 7-phase, 8-stage, 22-component pipeline; strictly serial build order
- **[[concepts/agent-vs-tool-classification]]** — 1 LLM agent (Agent E), 21 tools; cost and reliability principle
- **[[concepts/persona-layer]]** — per-tenant rich business profile; the competitive moat; TBD for all 3 tenants
- **[[concepts/confidence-first-class]]** — confidence as user-visible field; routing logic at 3 confidence bands
- **[[concepts/lineage-log]]** — non-negotiable audit trail; must be built before second agent
- **[[concepts/disqualification-gate]]** — score gates before bucketing; prevents wrong leads reaching HOT
- **[[concepts/score-decay]]** + **[[concepts/action-sla]]** — temporal enforcement of scoring; SLA breach → alert
- **[[concepts/adaptive-signal-lifecycle]]** — deferred to Sprint 2-3; needs real production data

## Key Entities

- [[entities/gamoft]] — builder and B2B self-tenant; AWS likely; Laravel vs Python/Node TBD
- [[entities/urvee-organics]] — B2C tenant; Instagram + WhatsApp; persona TBD
- [[entities/govmen]] — third tenant; everything TBD
- [[entities/anishekh]] — project lead and document owner

## Open Questions

1. **Technology stack:** Backend language (Laravel/Python/Node), LLM provider (OpenAI/Anthropic/Groq/NVIDIA NIM), secrets vault, observability tooling — all `[TBD]`
2. **Tenant personas:** All three personas are `[TBD]`; Govmen profile entirely unknown
3. **Confidence calculation method:** Self-reported by LLM? Signal completeness derived? Hybrid?
4. **LinkedIn API strategy:** Official vs scraping — compliance concern flagged but unresolved
5. **Intent classifier implementation:** Rules vs small LLM vs hybrid — `[TBD]`
6. **Human review queue UX:** In-chat vs separate admin screen?
7. **~50 additional TBDs** in Section 16 of [[sources/2026-lead-intelligence-engine-reference]]

## What to Read Next

- Define the Gamoft B2B persona (easiest — self-knowledge)
- Research LLM provider costs (per-lead estimate needed for budget)
- LinkedIn API compliance decision — blocks Agent B design
- Govmen discovery session — this tenant is entirely undefined
