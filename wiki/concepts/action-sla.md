---
type: concept
name: "Action SLA"
aliases: ["Add-on 4c", "SLA", "bucket SLA", "action timelines"]
tags: [sla, add-on-4, alerting, bucketing]
source_count: 1
last_updated: 2026-04-14
---

# Action SLA

## Definition

Time-bounded action windows tied to each lead bucket. Part of Add-on 4c, locked in v2.0. Makes scoring operationally enforceable — a HOT lead not acted on in 24 hours triggers an automated alert to the team lead.

## SLA Framework `[LOCKED]`

| Bucket | Action Window | Breach Consequence |
|--------|--------------|-------------------|
| HOT | 24 hours | Alert to team lead |
| WARM | 2–3 days | (alert mechanism TBD) |
| COLD | Weekly nurture | Passive |

## Open Decisions

- `[TBD]` — SLA alert delivery mechanism (chat message? email? both?)
- `[TBD]` — Whether SLAs are per-tenant configurable

## Why It Matters

Scoring without SLAs is just a recommendation. SLAs convert scoring into execution — they make the system accountable. A HOT lead that misses a 24h window starts to lose value; combined with [[concepts/score-decay]], inaction has measurable consequences.

## Evidence & Examples

- "Stale HOT lead (SLA breach) triggers automated alert to team lead." (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None identified. Interaction with per-tenant config: some tenants may want different SLA windows — this is a TBD.

## Related Concepts

- [[concepts/score-decay]] — inaction → decay → score drops; SLA is the trigger point
- [[concepts/lead-pipeline-architecture]] — SLA tracker is Phase 06 component (TOOL)
- [[concepts/disqualification-gate]] — disqualification happens before bucketing which happens before SLAs apply

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 04 (Add-on 4c), 11.2
