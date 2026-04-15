---
type: concept
name: "Adaptive Signal Lifecycle"
aliases: ["Add-on 7", "Add-ons 6/7/8", "signal integrity", "signal discovery"]
tags: [deferred, signals, adaptive, add-on-7, sprint-2-3]
source_count: 1
last_updated: 2026-04-14
confidence: low
---

# Adaptive Signal Lifecycle

## Definition

A deferred (Sprint 2-3) unified subsystem combining three mechanisms that together allow the signal vocabulary — the set of observable patterns the system uses to evaluate leads — to evolve automatically and safely over time. Combines Add-ons 6, 7, and 8.

**Status: `[DEFERRED]` — not in v2.0 scope.**

## Why These Three Are One Subsystem

All three mechanisms share:
- Same data infrastructure (`signal_lineage`, `signal_definitions` tables)
- Same user-facing surface (business-language confirmation — Add-on 8)
- Same purpose: evolving the signal vocabulary

Separating them would force duplicate jobs, duplicate tables, inconsistent state.

## Three Components

### (a) Trust Mechanism — Integrity Scoring

Continuously evaluates each signal's real-world performance via four pillars:

| Pillar | Weight | Threshold |
|--------|--------|-----------|
| Lift | 40% | Conversion rate ≥ 1.3× baseline |
| Sample Confidence | 25% | ≥ 50 leads with CI check |
| Stability | 25% | Rolling 4-week lift trend; 2 consecutive weeks < 1.0× → auto-deprecation |
| Independence | 10% | Co-occurrence with other signals < 80% |

Plus: biweekly LLM audit of 20 random leads where signal fired. < 85% extraction accuracy → `under_review`.

**Signal lifecycle states:**
```
shadow → candidate → active → under_review → deprecated
```
Only `candidate → active` requires human approval.

### (b) Discovery Mechanism

Biweekly background job examines **mis-bucketed leads** (predicted vs actual outcomes), passes raw data to LLM: *"What patterns do these leads share that our current signals miss?"* Proposed signals inserted at `shadow` state. Trust Mechanism evaluates them naturally. **LLM suggests, human approves. Never auto-promote.**

### (c) Feedback Mechanism — Reason-Tagged Signals

Every user-visible reason string (e.g., "Requested pricing twice") carries a hidden `signal_id` linking to the source agent and prompt version. When user marks a reason as wrong, the system routes it to a per-signal accuracy dashboard without the user knowing. User never sees signal names, schemas, or agents.

## Add-on 8 — Business-Language Confirmation

Single user touchpoint for the entire lifecycle. When a meaningful change is ready (new signal for promotion, old signal failing), orchestrator asks ONE conversational question:

> "Pichle 2 mahine mein noticed ki jo customers 'family health' mention karte hain woh 3x zyada convert ho rahe hain. Kya main aage se ye pattern consider karoon?"

Options: "Haan" / "Nahi" / "Aur data dikhao" — No technical surface exposed.

## Why Deferred

"Shadow mode needs real leads to shadow. Integrity scoring needs real conversion outcomes. Building on hypothetical data produces expensive random number generators." Prerequisite: 2-3 months of production data + established baseline conversion rates.

## Tables Needed (Deferred Schemas)

- `signal_lineage` — per-lead signal extractions with `signal_id` mapping
- `signal_integrity_metrics` — lift/stability/independence per signal per tenant
- `signal_feedback_events` — reason-level verdicts linked to signal_ids
- Extensions to `signal_definitions` — status, metrics, audit dates

## Tensions & Contradictions

None yet (not built). The design principle "LLM suggests, human approves" is a key guard against runaway automation.

## Related Concepts

- [[concepts/lineage-log]] — entire system depends on lineage data
- [[concepts/feedback-loop]] — Add-on 6 (three-layer feedback) is the entry point to this system
- [[concepts/agent-vs-tool-classification]] — discovery LLM is a limited, scheduled LLM call, not a persistent agent
- [[concepts/persona-layer]] — signals are evaluated per-tenant, not globally

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 17.2–17.7, 19.3, 19.4, 19.5
