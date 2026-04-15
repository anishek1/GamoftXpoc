---
type: concept
name: "Lead Pipeline Architecture"
aliases: ["7-phase pipeline", "8-stage flow"]
tags: [pipeline, architecture, agentic, multi-tenant]
source_count: 1
last_updated: 2026-04-14
---

# Lead Pipeline Architecture

## Definition

The end-to-end system for ingesting, enriching, scoring, and delivering lead intelligence. Structured as a **7-phase, 8-stage flow** with 22 components (1 LLM agent, 21 tools). User input enters via chat; output is ranked buckets (HOT/WARM/COLD) with explanations, delivered back to the same chat interface.

## The 8-Stage Flow

```
User Input
  → Orchestrator: Intent Detection + Persona Load      [Phase 00]
    → Agent A: Source Fetch (parallel)                 [Phase 01]
      → Agent B: Data Gather (internal + external)     [Phase 02]
        → Agent C: Normalise (unified schema)           [Phase 03]
          → Agent D: Prompt Construction                [Phase 04]
            → Agent E: LLM Enrichment + Scoring         [Phase 05]
              → Orchestrator: Output + SLA + Decay      [Phase 06]
                → State Store / Registry               [Phase 07]
```

## Lead Status Transitions

```
captured → fetched → gathered → normalised → prompt_ready → enriched → delivered
                                                           ↓
                                                 (or: human_review)
```

## Component Classification

All 22 components are classified as TOOL or LLM_AGENT. See [[concepts/agent-vs-tool-classification]] for the full matrix.

**Only Agent E is an LLM agent.** Every other component is deterministic tooling.

## Phase-by-Phase Summary

| Phase | Component | Type | Output Status |
|-------|-----------|------|---------------|
| 00 | Orchestrator (Intent + Persona) | TOOL | `intent_ready` |
| 01 | Agent A — Source Fetch | TOOL | `fetched` |
| 02 | Agent B — Data Gather | TOOL | `gathered` |
| 03 | Agent C — Normalise | TOOL | `normalised` |
| 04 | Agent D — Prompt Build | TOOL | `prompt_ready` |
| 05 | Agent E — LLM Scoring | LLM AGENT | `enriched` |
| 06 | Output / SLA / Decay / Feedback | TOOL | `delivered` |
| 07 | State Store + Registry | TOOL | (persisted) |

## Why It Matters

This architecture reflects the core design principle: **LLM only where judgment is needed.** Minimizing LLM calls to one per lead keeps the system affordable at scale while preserving the holistic, persona-aware scoring that makes it different from a rule-based CRM.

## Build Order `[LOCKED]`

Serial construction; each layer validates the one beneath:

1. Lead schema + state store
2. Personas table
3. Orchestrator skeleton with mock agent responses
4. Agent A (website source only)
5. Agent C (validates Agent A output)
6. Observability logging layer
7. Agent E (first end-to-end test)
8. Agent B + Agent D
9. Disqualification + Decay + SLA rules
10. Feedback loop v1
11. Add WhatsApp + Instagram to Agent A
12. Multi-tenant expansion

## Tensions & Contradictions

None identified yet.

## Related Concepts

- [[concepts/agent-vs-tool-classification]] — how each component is classified
- [[concepts/persona-layer]] — injected at Phase 04, drives Agent E judgment
- [[concepts/lineage-log]] — written at every phase; non-negotiable
- [[concepts/disqualification-gate]] — applied in Phase 05 before bucketing
- [[concepts/score-decay]] — background job after Phase 06
- [[concepts/action-sla]] — enforced post-delivery
- [[concepts/capability-registry]] — maps use case → agent list for Phase 07
- [[concepts/confidence-first-class]] — output of Phase 05
- [[concepts/feedback-loop]] — Phase 06 v1; three-layer version deferred
- [[concepts/adaptive-signal-lifecycle]] — deferred to Sprint 2-3

## Related Entities

- [[entities/gamoft]] — builder; B2B self-tenant
- [[entities/urvee-organics]] — B2C tenant
- [[entities/govmen]] — third tenant (TBD)

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 01, 03, 12, 14, 19
