---
type: analysis
question: "How should confidence be calculated in the Lead Intelligence Engine? Is enrichment-based confidence valid?"
date: 2026-04-17
tags: [confidence, lead-completeness, scoring, enrichment, routing, brainstorm]
sources_consulted: [sources/2026-lead-intelligence-engine-reference, concepts/confidence-first-class, sources/2026-intelligence-layer-design]
status: RESOLVED — 2026-04-22
---

# Confidence Scoring — Brainstorm & Resolution

**Question:** How exactly should confidence be calculated? Is deriving it from enrichment score valid?  
**Date:** 2026-04-17  
**Resolved:** 2026-04-22

---

## Resolution (2026-04-22)

The question is now closed. The answer is: **there is no confidence score.**

What the system has instead is a **lead completeness score** — a measure of how complete the enriched lead data was at the time of scoring. It answers: "did the Scoring Agent have enough data to work with?" — not "how certain is the LLM about its own output?"

**Final decisions, all locked:**

| Question | Answer |
|---|---|
| Is there a confidence score? | No |
| What field is in the ScoringOutput? | `lead_completeness: float (0.0–1.0)` |
| What does it measure? | Completeness of the enriched lead data passed to the Scoring Agent |
| Who calculates it? | The Output Schema Layer (S2's intelligence layer), not the LLM |
| Is it LLM self-reported certainty? | No — LLMs are poorly calibrated; self-reporting is not used |
| Is it enrichment-score-derived? | No — that was ruled out as circular (see brainstorm below) |
| Is it boundary-proximity-derived? | No — that proposal was set aside; completeness is simpler and more actionable |
| What does it drive? | The `needs_review` flag. If `lead_completeness` is below a threshold → `needs_review = true` → lead routed to human review queue |
| What is the threshold? | `[TBD — team decision; S2 suggests 0.6 or 0.75 as starting options]` |
| Does the routing logic (≥80%, 50–79%, <50% bands) still exist? | Yes — same three bands, same routing behaviour. The input changed (completeness not confidence), but the bands and outcomes are unchanged |

The full ScoringOutput schema is defined in [[sources/2026-intelligence-layer-design]] Section 3.4 and documented in [[concepts/intelligence-layer]].

The correction is propagated across: [[concepts/confidence-first-class]], [[analyses/orchestration-layer-spec]] Section 4.3 and 5, [[analyses/governance-observability-layer]] Sections 2, 3.2, 5.3, and 10.

**One item still open:** the exact lead completeness threshold — the value below which `needs_review` is set to true. This is a team decision after Month 1 baseline data.

---

## Brainstorm History (kept for context — shows why each approach was ruled out)

This section documents the reasoning path that led to the resolution above.

---

## Context (2026-04-17 session)

Confidence is Add-on 3 of the Lead Intelligence Engine v2.0. It was previously decided (2026-04-16) that confidence would be derived from the enrichment score. This session challenged that decision.

---

## What We Established (Agreed)

### 1. The System's Flow

```
Dev team defines signals + weights (per tenant, per persona)
         ↓
Enrichment pipeline runs → signals fire or don't (based on data availability)
         ↓
Enrichment Score = weighted sum of fired signals → Bucket (HOT / WARM / COLD)
         ↓
Confidence = ??? (this is what is under review)
```

### 2. Three Types of Uncertainty Exist

| Type | Meaning | Example |
|---|---|---|
| Data uncertainty | Not enough information | Only 2 of 8 signals fired |
| Signal uncertainty | Data is contradictory | High seniority but company shrinking |
| Boundary uncertainty | Score is near a bucket cutoff | Score of 72 when boundary is at 70 |

### 3. Weights Are Per-Tenant, Per-Persona

Signals and their weights are configured by the dev team based on the tenant's persona. This means any confidence formula must respect those weights — you cannot treat all signals as equal.

---

## The Key Problem We Identified

### Weighted Signal Coverage Is Circular

The first proposed formula was:

```
Confidence = sum(weights of signals that fired) / sum(all weights) × 100
```

**This is redundant.** If missing signals contribute 0 to the enrichment score, then:

- High enrichment score → many high-weight signals fired → high confidence
- Low enrichment score → few signals fired → low confidence

They move in the same direction always. **Confidence derived from signal coverage tells you nothing that the enrichment score doesn't already tell you.**

---

## The Insight That Emerged

The enrichment score and confidence answer **different questions**:

| | Question | Already captured by |
|---|---|---|
| Enrichment Score | How good is this lead? | Enrichment pipeline |
| Confidence | How stable is this lead's bucket assignment? | NOT captured yet |

The only scenario where confidence adds genuine new information:

**Two leads with the same enrichment score but different distance from a bucket boundary.**

| Lead | Score | Nearest Boundary | Confidence in Bucket |
|---|---|---|---|
| A | 85 | boundary at 70 | 15 pts away → stable HOT |
| B | 72 | boundary at 70 | 2 pts away → fragile HOT |

Lead B is barely HOT. One missing signal could flip it to WARM. The enrichment score alone doesn't surface this. Bucket proximity does.

### Revised Definition (Proposed, Not Locked)

```
Confidence = how far the enrichment score sits from the nearest bucket boundary
```

---

## What Was Still Unresolved in April 2026

At the time of the brainstorm, three things blocked a final answer:

1. Bucket boundaries were TBD (now locked: HOT ≥80, WARM ≥55, COLD <55)
2. Whether signal coverage plays any role (ruled out — circular with enrichment score)
3. Whether boundary proximity was the right framing (set aside — completeness is cleaner)

All three are resolved. See Resolution section above.

---

## What Changed From Previous Decision (2026-04-16)

| Before | After This Session |
|---|---|
| Confidence derived from enrichment score threshold | Enrichment-based confidence is circular — under review |
| Method: self-reported LLM certainty ruled out | Still ruled out |
| Method: weighted signal coverage proposed | Also ruled out — redundant with enrichment score |
| New proposal: boundary proximity | Not yet locked — bucket thresholds needed first |

---

## Remaining Open Item

- **Lead completeness threshold** — the exact value below which `needs_review = true`. S2 suggests 0.6 or 0.75 as starting options. Team decision after Month 1 baseline data.
