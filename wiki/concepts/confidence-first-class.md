---
type: concept
name: "Confidence as First-Class Field"
aliases: ["Add-on 3", "confidence score", "confidence routing"]
tags: [scoring, confidence, ux, add-on-3, human-in-the-loop]
source_count: 1
last_updated: 2026-04-17
confidence: low
status: UNDER REVIEW — calculation method not locked, see analyses/confidence-scoring-brainstorm
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

`[UNDER REVIEW — 2026-04-17]` See full brainstorm: [[analyses/confidence-scoring-brainstorm]]

**Previous decision (2026-04-16):** Confidence derived from enrichment score threshold. This has been challenged.

**Problem identified:** Enrichment-based confidence is circular. If missing signals already contribute 0 to the enrichment score, then confidence and enrichment score move in the same direction always — confidence adds no new information.

**Current best proposal:** Confidence = distance of the enrichment score from the nearest bucket boundary (HOT/WARM/COLD threshold). This captures something the enrichment score does not — how stable the bucket assignment is.

**Blocker:** Bucket thresholds are `[TBD]`. Confidence formula cannot be finalised until boundaries are locked.

**Still confirmed:**
- LLM self-reported confidence is NOT used (LLMs are poorly calibrated)
- Weighted signal coverage is NOT used (redundant with enrichment score)

## Edge Cases `[LOCKED]`

- **Human review queue fills up and nobody reviews:** Set SLA alert — if lead in human review > N hours (N = `[TBD]`) without action, escalate to team lead. Stale unreviewed leads are as bad as wrong scores.

## Evidence & Examples

- "Two leads scoring 85 needing different actions based on confidence. Score without confidence is overconfident and destroys sales team trust faster than honest uncertainty." (source: [[sources/2026-lead-intelligence-engine-reference]])
- Making confidence user-visible is called the differentiator in the source doc. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None. Previous open question around LLM self-reported confidence being poorly calibrated is resolved — self-reporting is not used.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — confidence is output of Phase 05 (Agent E)
- [[concepts/lineage-log]] — confidence stored per lead per step in lineage
- [[concepts/disqualification-gate]] — disqualification applied before confidence routing
- [[concepts/feedback-loop]] — feedback outcomes over time inform confidence calibration

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 02, 04 (Add-on 3), 10.3, 10.4, 19.9
