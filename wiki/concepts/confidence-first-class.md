---
type: concept
name: "Confidence as First-Class Field"
aliases: ["Add-on 3", "confidence score", "confidence routing", "lead completeness score", "needs_review"]
tags: [scoring, confidence, completeness, ux, add-on-3, human-in-the-loop]
source_count: 2
last_updated: 2026-04-22
confidence: medium
status: CORRECTION APPLIED 2026-04-22 — "confidence" field is a lead completeness score; calculation method still being locked
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

## Correction (2026-04-22): This is a Lead Completeness Score, Not LLM Confidence

**Confirmed decision:** The field previously called "confidence" is a **lead completeness score** — how complete and usable the enriched lead data is. It is **not** a measure of how certain the LLM is about its own scoring output.

This resolves the circular-enrichment problem identified in the 2026-04-17 review: if missing signals already contribute 0 to the enrichment score, then LLM-self-reported confidence adds no new information and is poorly calibrated anyway.

**What lead completeness score measures:** the completeness of the enriched lead data passed into the scoring prompt — whether all five scoring dimensions have sufficient signal to reason over meaningfully.

**What it does NOT measure:** the LLM's own certainty about the score it assigned (LLMs are poorly calibrated on this).

**Routing logic unchanged:** the `needs_review` flag and the three confidence bands still apply, but the input is lead data completeness, not LLM certainty.

**Still open:** The exact formula for lead completeness and the threshold below which `needs_review = true` are not yet locked. See [[analyses/confidence-scoring-brainstorm]].

**Still confirmed:**
- LLM self-reported confidence is NOT used (LLMs are poorly calibrated)
- Enrichment-score-as-confidence is NOT used (circular — it adds no new information)
- Lead completeness score IS the field — definition and threshold `[TBD]`

## Edge Cases `[LOCKED]`

- **Human review queue fills up and nobody reviews:** Set SLA alert — if lead in human review > N hours (N = `[TBD]`) without action, escalate to team lead. Stale unreviewed leads are as bad as wrong scores.

## Evidence & Examples

- "Two leads scoring 85 needing different actions based on confidence. Score without confidence is overconfident and destroys sales team trust faster than honest uncertainty." (source: [[sources/2026-lead-intelligence-engine-reference]])
- Making confidence user-visible is called the differentiator in the source doc. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None. Previous open question around LLM self-reported confidence being poorly calibrated is resolved — self-reporting is not used.

## Related Concepts

- [[concepts/intelligence-layer]] — Output Schema Layer applies the completeness gate; sets `needs_review = true`; `lead_completeness` is a field in ScoringOutput
- [[concepts/lead-pipeline-architecture]] — completeness score is output of the Scoring Agent (Pipeline 1 stage 5)
- [[concepts/lineage-log]] — completeness score stored per lead in lineage
- [[concepts/disqualification-gate]] — disqualification applied before completeness routing
- [[concepts/feedback-loop]] — feedback outcomes over time should inform completeness threshold calibration

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 02, 04 (Add-on 3), 10.3, 10.4, 19.9
- [[sources/2026-intelligence-layer-design]] — Section 3.4 Output Schema Layer; Section 7 (completeness gate open decision)
