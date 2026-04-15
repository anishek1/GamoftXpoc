---
type: source
title: "Multi-Tenant Adaptive Lead Intelligence Engine — Master Reference"
source_file: raw/assets/lead_intelligence_engine_reference.md
date_ingested: 2026-04-14
tags: [lead-intelligence, agentic, multi-tenant, poc-planning, gamoft, pipeline-architecture]
---

# Multi-Tenant Adaptive Lead Intelligence Engine — Master Reference

**Source:** raw/assets/lead_intelligence_engine_reference.md  
**Ingested:** 2026-04-14  
**Type:** reference doc (pre-planning, not PRD)  
**Owner:** [[entities/anishekh]] | **Org:** [[entities/gamoft]]  
**Version:** v2.0 | **Status:** Pre-planning — source of truth for ticket-driven discussions  

---

## Summary

This is the single source of truth compiled from all pre-planning discussions for the Multi-Tenant Adaptive Lead Intelligence Engine (v2.0). It documents every architectural decision, design principle, open question (`[TBD]`), and deferred item across 20 sections. It is intentionally not a PRD — it feeds ticket-by-ticket discussions after which final specification documents will be derived.

The system is a production-grade agentic pipeline that ingests leads from WhatsApp, Instagram, and Website; enriches them with internal and public data; scores them using tenant-specific LLM-driven personas; and delivers ranked buckets (HOT/WARM/COLD) with explanations inside a chat interface where salespeople already work.

Three tenants are in scope for the POC: **[[entities/urvee-organics]]** (B2C), **[[entities/gamoft]]** (B2B self-tenant), and **[[entities/govmen]]** (profile `[TBD]`).

The architectural north star is **minimal LLM usage**: only one true LLM agent (Agent E — LLM Enrichment & Scoring) out of 22 total components. Everything else is deterministic tooling. This keeps costs predictable, execution fast, and debugging straightforward.

---

## Key Claims

- **1 LLM agent, 21 tools** — only Agent E uses an LLM; all orchestration, fetching, normalizing, and prompt construction is deterministic. (source: `[LOCKED]` Add-on 1, Sections 03 and 14)
- **5 design principles drive all decisions:** user lives in chat (no technical surfaces), LLM only where judgment needed, isolated persona per tenant, confidence as visible field, every transformation writes to lineage log.
- **Persona is the competitive moat** — same lead scores differently across tenants by design. Without persona, this is just a generic CRM.
- **Confidence is first-class and user-visible** — score alone is not actionable. Two leads at 85 with 90% vs 40% confidence require completely different actions.
- **Lineage log is non-negotiable** — must be built before the second agent, not retrofitted. Per lead, per step: input snapshot, output snapshot, prompt version, confidence.
- **Postgres-only state store** — no Kafka, Redis Streams, or queues at current scale (dozens of leads/hour, not thousands).
- **Disqualification gates** override scoring before bucketing: `serviceability=0` hard-caps at 50, wrong geo -30, non-decision-maker -40, student/spam → 0.
- **Score Decay** runs as background job: -10 after 7d inactivity, -20 after 14d no response, auto-cold after 30d dormant.
- **Action SLAs** are bucket-tied and enforceable: HOT=24h, WARM=2-3d, COLD=weekly nurture.
- **Adaptive Signal Lifecycle (Add-ons 6/7/8) deliberately deferred** — needs 2-3 months of real production data to measure anything meaningful.
- **Build order is strictly serial** — each layer validates the one beneath; every sprint ends deployable.

---

## Entities Mentioned

- [[entities/gamoft]] — B2B self-tenant; owner/builder of the system; Anishekh is the owner
- [[entities/urvee-organics]] — B2C tenant (organic products); has Instagram + WhatsApp presence
- [[entities/govmen]] — third POC tenant; profile unknown `[TBD]`
- [[entities/anishekh]] — document owner; manager who led the pre-planning discussions

---

## Concepts Mentioned

- [[concepts/agent-vs-tool-classification]] — every component tagged LLM_AGENT or TOOL; only Agent E is LLM
- [[concepts/persona-layer]] — per-tenant rich business profile; drives prompt construction and scoring
- [[concepts/confidence-first-class]] — confidence promoted from internal signal to user-visible field
- [[concepts/lead-pipeline-architecture]] — 7-phase, 8-stage flow from input to bucketed output
- [[concepts/lineage-log]] — immutable audit trail per lead per agent step; non-negotiable
- [[concepts/disqualification-gate]] — critical score overrides applied before bucketing
- [[concepts/score-decay]] — background job that degrades stale scores over time
- [[concepts/action-sla]] — time-bounded action windows per bucket tied to alerts
- [[concepts/capability-registry]] — maps use case → ordered list of agent IDs; extensibility pattern
- [[concepts/adaptive-signal-lifecycle]] — deferred Add-ons 6/7/8: feedback, integrity scoring, signal discovery
- [[concepts/feedback-loop]] — v1: single-tap outcome tagging; v2 (deferred): three-layer architecture

---

## Questions Raised

- Technology stack not decided: backend language (Laravel vs Python vs Node), LLM provider (OpenAI/Anthropic/Groq/NVIDIA NIM), secrets vault, observability tooling, hosting.
- Intent classifier implementation: rule-based vs small LLM vs hybrid — `[TBD]`
- Full persona definition for all three tenants — requires tenant interviews for Urvee and Govmen
- How confidence is calculated: self-reported by LLM? derived from signal completeness? both?
- LinkedIn API compliance strategy — official vs scraping, chat flagged concerns
- Human review queue UX — in-chat vs separate admin screen?
- Exact disqualification rule set per tenant — currently only generic rules locked
- ~50+ additional `[TBD]` items tracked in Section 16 (Open Decisions Registry)

---

## Quotes

> "User ko agents ka pata nahi chalega. Woh sirf chat mein baat karta hai. Signals, schemas, agents — sab hidden."

> "Building on hypothetical data produces expensive random number generators." — on why adaptive layer is deferred

> "The user interface and the diagnostic interface are not the same interface." — on reason-tagged signals

> "Start with Postgres. You do not need Kafka, Redis Streams, or a message queue at your current scale."

> "Build lineage logging BEFORE adding the second agent, not after the eighth. Cost is low early, enormous when retrofitting."

> "Adding new use case = (1) build new agents, (2) test in isolation, (3) add one line to registry config. Orchestrator requires ZERO changes."
