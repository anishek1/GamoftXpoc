---
type: analysis
question: "Define consistency metrics as part of the scoring quality metrics story."
date: 2026-04-17
tags: [consistency, scoring-quality, kpi, metrics, determinism, drift, decay]
sources_consulted: [sources/2026-lead-intelligence-engine-reference]
status: complete
---

# Consistency — Metric Group Card

**Question:** Does the system produce the same result for the same lead, and do scores only change when something actually changes about the lead?
**Date:** 2026-04-17
**Part of story:** Define scoring quality metrics → Sub-story: Consistency

---

## Context

This is the second of three sub-stories under "Define scoring quality metrics." The other two are accuracy proxy (complete) and action relevance (next).

Consistency metrics validate that the scoring pipeline is stable and deterministic. A score is only useful if it means the same thing every time it is produced. Inconsistency can appear in five distinct ways in this system — cross-run noise, temporal drift, boundary fragility, decay coherence failures, and signal calculation instability.

Available data: historical score records, lineage log (signals fired, score per step, decay events, rescore events), scoring output.

---

## Primary Metrics

These are tracked, owned, and reviewed on a monthly cadence.

---

### C1 — Cross-Run Bucket Stability

**Definition:**
Take leads that were re-scored with no data change between runs. Of those, count how many landed in the same bucket both times. Divide by the total number of re-scored leads with no data change.

**What it tells you:**
This is the core determinism check. If the same lead with the same data keeps getting different buckets, you cannot trust any individual score — the system is noisy at the output level.

**Target:**
TBD after Month 1 baseline. Should be very high by design.

**Data needed:**
Historical score records, lineage log (to confirm no data change between runs).

---

### C2 — Temporal Score Drift

**Definition:**
From historical score records, identify leads whose underlying data did not change between two time periods. Measure how much their scores changed anyway.

**What to track:**
Two things — what percentage of those leads saw any score change at all, and for those that did change, what was the average magnitude of the change.

**What it tells you:**
Ideally both numbers are zero or near zero. Any consistent drift without data change points to silent model behavior changes — LLM responses shifting, signal extraction behaving differently, or a background process touching scores it should not.

**Target:**
TBD after Month 1 baseline.

**Data needed:**
Historical score records, lineage log (to confirm no data change between periods).

---

## Diagnostic Checks

These are not tracked as KPIs. They are pass/fail checks run alongside the primary metrics to diagnose what is wrong when primary metrics look bad.

---

### C3 — Boundary Flip Rate

**Definition:**
Of leads sitting close to a bucket boundary, how many flip between buckets on re-score without any data change?

**Status:**
Blocked until bucket score thresholds are defined. Once HOT/WARM/COLD boundaries are set, the danger zone around each boundary can be defined and leads within it can be flagged and tracked.

**What failure means:**
The bucket boundaries are too tight or the scoring pipeline has variance at the boundary level. May require a confidence buffer zone around boundaries.

**Revisit when:**
Bucket score thresholds are locked.

---

### C4 — Decay-Rescore Coherence

**Definition:**
The system applies score decay on a fixed schedule — minus 10 at 7 days, minus 20 at 14 days, auto-cold at 30 days. After a decay event fires and a lead is rescored, the actual score change should match the expected decay amount.

**How to check:**
From the lineage log, for every decay event, compare the score before and after. If the delta is significantly larger or smaller than the expected decay amount, something other than decay is influencing the rescore.

**Pass condition:**
Actual score delta after decay is within an acceptable range of the expected decay amount. Acceptable range to be defined once baseline variance is known.

**What failure means:**
Something other than decay is influencing the rescore — a coherence failure in the pipeline.

**Data needed:**
Lineage log (decay events, score before and after rescore).

---

### C5 — Signal Contribution Consistency

**Definition:**
For any given signal with a defined weight, its contribution to the enrichment score should be identical every time it fires with the same value, regardless of which lead it is for.

**Pass condition:**
Same signal, same weight, same input value always produces the same score contribution.

**What failure means:**
The enrichment score calculation is not deterministic. This corrupts all other metrics upstream. Stop and fix before trusting any output.

**Note:**
This is an engineering-level check, not a product KPI. Should be verified as a unit test during build and spot-checked monthly from the lineage log.

**Data needed:**
Lineage log (signal values, weights, score contributions per lead).

---

## Action Rules

If C1 drops: do not investigate signal weights first. The problem is in the LLM call or the scoring pipeline — check temperature settings, prompt stability, and whether any non-deterministic element was introduced.

If C2 shows drift: check for silent changes — model version updates, signal extraction logic changes, or any background job touching score fields. Drift without data change is always a pipeline problem, not a lead data problem.

If C3 flags many boundary flips once thresholds are defined: bucket boundaries may need widening, or a confidence buffer zone around boundaries needs to be introduced.

If C4 fails: the rescore logic after decay is broken. The lineage log should identify exactly which step is producing the unexpected delta.

If C5 fails: stop everything. The enrichment score calculation is not reliable. Fix before trusting any other output.

---

## Data Sources

Historical score records, lineage log (signals fired per lead, score per step, decay events, rescore events), scoring output.

---

## Review Cadence

Monthly for C1 and C2. C4 checked after every decay cycle. C5 verified at build time and spot-checked monthly.

---

## Owner

AI/ML owner. Engineering lead owns C5.

---

## Related Pages

- [[analyses/accuracy-proxy-metrics]] — previous sub-story; shares data sources
- [[concepts/score-decay]] — decay schedule referenced in C4
- [[concepts/confidence-first-class]] — boundary sensitivity in C3 ties to confidence routing bands
- [[analyses/confidence-scoring-brainstorm]] — bucket boundary thresholds (TBD) are a shared blocker for C3
- [[sources/2026-lead-intelligence-engine-reference]] — decay schedule and lineage log spec
