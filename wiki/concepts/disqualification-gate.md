---
type: concept
name: "Disqualification Gate"
aliases: ["Add-on 4a", "disqualification", "score override"]
tags: [scoring, add-on-4, rules, bucketing]
source_count: 1
last_updated: 2026-04-14
---

# Disqualification Gate

## Definition

Critical override rules applied **before bucketing**, after Agent E scores a lead. Certain conditions prevent a lead from reaching the HOT bucket regardless of its raw score. Part of Add-on 4a, locked in v2.0.

These are not just negative signals — they are **gates** that hard-cap or zero-out scores for leads that should never reach a salesperson as high-priority.

## Current Rules `[LOCKED — generic]`

| Condition | Effect |
|-----------|--------|
| `serviceability = 0` | Hard cap score at 50 (or mark as disqualified) |
| Wrong geography | Score -30 |
| Non-decision-maker | Score -40 |
| Student / spam / irrelevant | Auto-discard (score → 0) |

Per-tenant disqualification rule sets are `[TBD]` — the above are generic starting rules.

## Where in Pipeline

Applied in Phase 05 (Agent E's output) or Phase 06 (before bucketing). Implemented as a TOOL (deterministic rule evaluation), not an LLM call.

## Why It Matters

Without disqualification gates, a highly engaged student with no purchasing power could end up in the HOT bucket, wasting salesperson time. Disqualification enforces business reality on top of engagement signals.

## Evidence & Examples

- "These are not just negative signals — they are gates that prevent wrong leads from reaching HOT bucket." (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

- Tension with [[concepts/confidence-first-class]]: a lead with `serviceability=0` hard-capped at 50 but high engagement signals may generate a misleading confidence score. How confidence is reported for disqualified leads needs definition.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — gate applied in Phase 05/06
- [[concepts/persona-layer]] — `negative_signals` in persona feed disqualification rules
- [[concepts/score-decay]] — works alongside decay to keep scores realistic over time
- [[concepts/action-sla]] — bucketing feeds SLAs

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 04 (Add-on 4a), 10.2
