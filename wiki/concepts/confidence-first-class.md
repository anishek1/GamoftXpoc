---
type: concept
name: "Confidence as First-Class Field"
aliases: ["Add-on 3", "confidence score", "confidence routing"]
tags: [scoring, confidence, ux, add-on-3, human-in-the-loop]
source_count: 1
last_updated: 2026-04-14
---

# Confidence as First-Class Field

## Definition

Confidence is the system's trust in its own score, expressed as a percentage (0-100%). Add-on 3 of v2.0, locked. It is **promoted from an internal routing signal to a user-visible field** on every lead card, shown alongside the score.

The core insight: **two leads scoring 85 are not the same if one has 90% confidence and the other has 40%.** Score without confidence is overconfident and destroys sales team trust faster than honest uncertainty.

## Routing Logic `[LOCKED]`

| Confidence | Behavior |
|---|---|
| ≥ 80% | Auto-bucket; write directly to output |
| 50–79% | Bucket with warning flag; suggest human review |
| < 50% | Route to human review queue; do NOT auto-bucket |

## User-Visible Format

Every lead card shows: `score + confidence`  
Example: "Score: 85 | Confidence: 72% — review recommended"

## How Confidence Is Calculated

`[TBD]` — three candidates under consideration:
1. Self-reported by Agent E (LLM states its own confidence)
2. Derived from signal completeness (sparse data = low confidence)
3. Hybrid of both

## Edge Cases `[LOCKED]`

- **Human review queue fills up and nobody reviews:** Set SLA alert — if lead in human review > N hours (N = `[TBD]`) without action, escalate to team lead. Stale unreviewed leads are as bad as wrong scores.

## Evidence & Examples

- "Two leads scoring 85 needing different actions based on confidence. Score without confidence is overconfident and destroys sales team trust faster than honest uncertainty." (source: [[sources/2026-lead-intelligence-engine-reference]])
- Making confidence user-visible is called the differentiator in the source doc. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None yet. Open question: if confidence is self-reported by the LLM, it may not be well-calibrated. Needs empirical testing once Agent E is live.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — confidence is output of Phase 05 (Agent E)
- [[concepts/lineage-log]] — confidence stored per lead per step in lineage
- [[concepts/disqualification-gate]] — disqualification applied before confidence routing
- [[concepts/feedback-loop]] — feedback outcomes over time inform confidence calibration

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 02, 04 (Add-on 3), 10.3, 10.4, 19.9
