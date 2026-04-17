---
type: analysis
question: "Define accuracy proxy metrics as part of the scoring quality metrics story."
date: 2026-04-17
tags: [accuracy-proxy, scoring-quality, kpi, metrics, bucketization]
sources_consulted: [sources/2026-lead-intelligence-engine-reference]
status: complete
---

# Accuracy Proxy — Metric Group Card

**Question:** Did HOT leads actually perform better than WARM, and WARM better than COLD — in real outcomes?
**Date:** 2026-04-17
**Part of story:** Define scoring quality metrics → Sub-story: Accuracy proxy

---

## Context

This is one of three sub-stories under "Define scoring quality metrics" (part of the broader "Define success metrics" story). The other two are consistency and action relevance.

Accuracy proxy metrics are designed to validate bucket assignments against real-world outcomes. The system has no ground truth at scoring time — we cannot know whether a lead is truly HOT until the salesperson acts on it. These metrics use CRM and feedback data as a proxy for ground truth after the fact.

**Positive outcome definition:** Any one of the following qualifies as a positive outcome, treated equally — responded to outreach, meeting booked, lead qualified by salesperson, deal closed, salesperson gave thumbs up.

**Working assumption:** We are operating on real bucketization output data, not a day 0 baseline.

---

## Primary Metrics

These are tracked, owned, and reviewed on a monthly cadence.

---

### AP1 — Bucket Outcome Rate (BOR)

**Definition:**
For each bucket, the percentage of leads that resulted in at least one positive outcome. A positive outcome is any one of: responded to outreach, meeting booked, lead qualified by salesperson, deal closed, or salesperson thumbs up. These are treated as equal — any single one qualifies.

**How it is calculated:**
Count the leads in a bucket that had a positive outcome. Divide by the total number of leads in that bucket. Do this separately for HOT, WARM, and COLD. You get three numbers.

**What it tells you:**
Whether each bucket is producing real results. A HOT bucket with a low outcome rate means the system is mislabeling leads as high priority.

**Target:**
TBD after Month 1 baseline. No number is set upfront.

**Data needed:**
Scoring output (bucket per lead), CRM outcome events, salesperson feedback.

---

### AP2 — Bucket Separation

**Definition:**
Two things checked together from the same BOR values — whether the bucket order is correct, and whether the gap between buckets is meaningful.

**What it checks:**

First — order: HOT outcome rate must be greater than WARM, and WARM greater than COLD. If this fails, the buckets are miscalibrated regardless of anything else.

Second — magnitude: HOT outcome rate divided by COLD outcome rate, tracked over time. A ratio close to 1 means the system is barely better than random assignment even if the order is technically correct.

**What it tells you:**
A system can be directionally correct and practically useless at the same time. Order alone does not confirm the system is adding value. The ratio is what tells you whether the separation is meaningful enough to act on.

**How to report:**
Both are reported together. A passing result: order is correct, ratio is X. A failing result flags which of the two broke.

**Target:**
TBD after Month 1 baseline.

**Data needed:**
BOR values from AP1 — no additional data required.

---

## Diagnostic Checks

These are not tracked as KPIs. They are pass/fail checks run alongside the primary metrics to diagnose what is wrong when primary metrics look bad.

---

### AP3 — Completeness Qualifier

**Definition:**
A check that within the same bucket, leads where more signals fired performed better than leads where fewer signals fired.

**Pass condition:**
Within each bucket, leads with above-median signal completeness have a higher outcome rate than leads with below-median signal completeness.

**What failure means:**
Completeness of data is not a meaningful signal in this system. It is already fully captured by the enrichment score and adds nothing on top of it.

**What to do if it fails:**
Drop completeness as a tracked field. Do not use it in reporting or routing logic.

---

## Action Rules

If AP2 order check fails: do not change signal weights yet. First audit bucket score boundaries — the boundaries are the likely cause, not the signals themselves.

If AP2 ratio is near 1: the scoring engine is not creating meaningful separation between leads. Review signal selection and weights with the tenant persona team before any model changes.

If AP3 fails: remove completeness from the metric set going forward. Do not use it as a proxy for confidence.

If AP1 shows HOT below 30% outcome rate after baseline is established: trigger a full scoring audit — signals, weights, and persona configuration.

---

## Data Sources

Scoring output, lineage log (signals fired per lead), CRM outcome events, salesperson feedback data.

---

## Review Cadence

Monthly. Minimum 100 outcomes per bucket before any review is considered valid.

---

## Owner

AI/ML owner. Product owner co-reviews monthly.

---

## Related Pages

- [[concepts/confidence-first-class]] — confidence routing is adjacent to accuracy; bucket boundaries (TBD) affect both
- [[analyses/confidence-scoring-brainstorm]] — bucket boundary decision is a shared blocker
- [[sources/2026-lead-intelligence-engine-reference]] — source system architecture
