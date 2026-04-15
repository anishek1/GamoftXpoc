---
type: concept
name: "Score Decay"
aliases: ["Add-on 4b", "decay job", "score degradation"]
tags: [scoring, add-on-4, background-job, staleness]
source_count: 1
last_updated: 2026-04-14
---

# Score Decay

## Definition

A background job that automatically degrades lead scores over time when there is no activity or response. Part of Add-on 4b, locked in v2.0. Prevents stale scores from persisting indefinitely and misleading salespeople.

## Decay Rules `[LOCKED]`

| Condition | Effect |
|-----------|--------|
| No activity for 7 days | Score -10 |
| No response for 14 days | Score -20 |
| Dormant > 30 days | Auto-move to COLD bucket |

## Open Decisions

- `[TBD]` — Decay job schedule (hourly vs daily)
- `[TBD]` — Whether decay rules differ per tenant

## Why It Matters

A HOT lead from 3 weeks ago with no follow-up is not HOT anymore. Without decay, the score list becomes a graveyard of stale priorities. Decay enforces temporal reality on the scoring system.

## Evidence & Examples

- Decay works in tandem with Action SLAs ([[concepts/action-sla]]): if a HOT lead triggers an SLA alert (24h no action) and then still receives no action, decay begins to drop its score, eventually cooling it to WARM or COLD. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None identified yet. Interaction between decay and [[concepts/disqualification-gate]] should be tested: can a decayed lead cross a disqualification threshold that wasn't triggered at initial scoring?

## Related Concepts

- [[concepts/action-sla]] — SLAs set the urgency; decay enforces the consequence of missing them
- [[concepts/disqualification-gate]] — applied at scoring time; decay runs afterwards continuously
- [[concepts/lead-pipeline-architecture]] — decay job is Phase 06 output layer
- [[concepts/feedback-loop]] — decay behavior should eventually be tunable via feedback

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 04 (Add-on 4b), 11.3
