---
type: analysis
question: "Define action relevance metrics as part of the scoring quality metrics story."
date: 2026-04-17
tags: [action-relevance, scoring-quality, kpi, metrics, sla, salesperson-behaviour]
sources_consulted: [sources/2026-lead-intelligence-engine-reference]
status: complete
---

# Action Relevance — Metric Group Card

**Question:** Are salespeople acting on leads in the right order, at the right speed, with the right type of action?
**Date:** 2026-04-17
**Part of story:** Define scoring quality metrics → Sub-story: Action relevance

---

## Context

This is the third and final sub-story under "Define scoring quality metrics." The other two are accuracy proxy (complete) and consistency (complete).

Action relevance metrics validate that the scoring output is actually influencing salesperson behaviour. A score that is accurate and consistent but ignored by the sales team produces no business value. These metrics bridge the system output and the human response.

Available data: scoring output (bucket per lead), action timestamps, action type logs, salesperson ID per action, CRM event logs, salesperson feedback.

---

## Primary Metrics

These are tracked, owned, and reviewed on a monthly cadence.

---

### AR1 — SLA Compliance Rate

**Definition:**
The system defines action windows per bucket — HOT within 24 hours, WARM within 2–3 days, COLD within the weekly batch. For each bucket, the percentage of leads first actioned within their SLA window.

**How it is calculated:**
Using the action timestamp against the score assignment timestamp gives the exact time-to-action per lead. Leads that breached their window are SLA failures. Calculate separately for HOT, WARM, and COLD.

**Open decision:**
The WARM SLA is defined as 2–3 days. A single cutoff needs to be locked — 48 hours or 72 hours — before this metric can be calculated.

**What it tells you:**
Whether the system's action guidance is being followed operationally. HOT compliance is the most critical — a missed HOT lead is a missed high-priority opportunity.

**Target:**
TBD. To be set by product owner and team leads after reviewing Month 1 data. Note: unlike other metrics, SLA targets can be set early since the SLA windows themselves are already defined.

**Data needed:**
Score assignment timestamps, action timestamps, bucket per lead.

---

### AR2 — Action Rate by Bucket

**Definition:**
Of all leads in each bucket, the percentage that received any action at all.

**What it tells you:**
Whether salespeople are using the score to prioritise. HOT leads must have the highest action rate, WARM second, COLD lowest. If COLD leads are actioned at the same rate as HOT, the scoring output is being ignored.

**Monotonicity check:**
HOT action rate must be greater than WARM, WARM greater than COLD. A violation means the score is not influencing salesperson behaviour — this is a system adoption problem, not a scoring accuracy problem.

**Target:**
TBD after Month 1 baseline.

**Data needed:**
Scoring output (bucket per lead), action logs.

---

## Diagnostic Checks

These are not tracked as KPIs. They are run alongside primary metrics to diagnose the cause when primary metrics flag a problem.

---

### AR3 — Time-to-Action Distribution

**Definition:**
For each bucket, the spread of time-to-first-action across all leads — not just whether the SLA was met, but how the times are distributed.

**What it tells you:**
A healthy HOT bucket has most leads clustered near the 24-hour mark. A long tail — some leads actioned in 2 hours, others in 48 — means leads are being batched rather than prioritised continuously. The tail is where SLA breaches and lost opportunities live.

This gives more information than SLA compliance alone. Two buckets can both be at 80% compliance but have very different distributions underneath.

---

### AR4 — Action Type Distribution by Bucket

**Definition:**
Breakdown of action types taken per bucket — calls, emails, meetings, etc.

**Pass condition:**
Action intensity should decrease as bucket priority decreases. HOT leads should attract higher-intensity actions (calls, meetings). If HOT leads are mostly receiving emails while WARM leads are getting calls, the score is not driving the right behaviour.

**What failure means:**
Either salespeople do not trust the score or the interface is not making priority visible enough. This is a UX and training issue, not a scoring issue.

**Note:**
What counts as "higher intensity" needs to be defined by the team based on the action types available in the system.

---

### AR5 — Salesperson Priority Alignment

**Definition:**
For each salesperson, in sessions where leads from multiple buckets were available, whether they actioned the highest-bucket lead first.

**What it tells you:**
A salesperson who consistently actions WARM leads before HOT leads is either ignoring the score or has a workflow that does not surface priorities clearly. This surfaces individual behaviour patterns that aggregate metrics hide.

**What failure means:**
If one or two salespeople show low alignment — coaching issue. If it is systemic across all salespeople — the interface is not surfacing priorities clearly enough.

---

## Action Rules

If AR1 shows HOT compliance dropping: check whether the team lead SLA breach alert is firing correctly. If it is firing and compliance is still low, the problem is workload capacity, not system failure.

If AR2 shows low action rate for HOT: the score is not influencing salesperson behaviour. Investigate whether scores are visible in the workflow before questioning the scores themselves.

If AR3 shows a long tail for HOT: leads are being queued and worked in batches instead of immediately. This is a workflow and prioritisation problem.

If AR4 shows action type mismatch: raise with product owner — this is a UI and training issue, not a scoring issue.

If AR5 shows low alignment for specific salespeople: flag for team lead review. If systemic across all salespeople, review how scores are surfaced in the interface.

---

## Data Sources

Scoring output, action timestamps, action type logs, salesperson ID per action, CRM event logs.

---

## Review Cadence

Monthly for AR1 and AR2. AR3 and AR4 reviewed quarterly or when AR1/AR2 flag a problem. AR5 reviewed monthly and shared with team leads.

---

## Owner

Product owner. Team leads own AR5 follow-through.

---

## Related Pages

- [[analyses/accuracy-proxy-metrics]] — first sub-story; shares CRM and feedback data sources
- [[analyses/consistency-metrics]] — second sub-story; shares scoring output data
- [[concepts/action-sla]] — SLA windows referenced in AR1
- [[sources/2026-lead-intelligence-engine-reference]] — action SLA definitions (Sections 04, Add-on 4c)
