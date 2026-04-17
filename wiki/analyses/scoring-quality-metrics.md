---
type: analysis
question: "Define scoring quality metrics as part of the Define Success Metrics story."
date: 2026-04-17
tags: [scoring-quality, accuracy-proxy, consistency, action-relevance, kpi, metrics]
sources_consulted: [sources/2026-lead-intelligence-engine-reference]
status: complete
---

# Scoring Quality Metrics

**Story:** Define success metrics → Sub-story: Define scoring quality metrics
**Date:** 2026-04-17
**Sub-stories covered:** Score Coverage, Accuracy Proxy, Consistency, Action Relevance

---

## Score Coverage Rate

**Question this metric answers:**
Are all eligible leads actually being scored, or is the pipeline silently dropping some before they reach a bucket?

**Definition:**
Of all eligible leads that entered the pipeline, the percentage that were successfully scored and assigned a bucket. This is a prerequisite check — all other metrics in this document only measure leads that made it through scoring. If a significant portion of leads are dropping out silently, every downstream metric is measuring an incomplete picture.

**Formula:**

```
Score Coverage Rate = (Leads Successfully Scored / Total Leads Entered Pipeline) × 100
```

**Variables:**

`Leads Successfully Scored` — count of leads that received a bucket assignment (HOT, WARM, or COLD) by the end of the pipeline run.
Source: scoring output table; count leads with a non-null bucket value.

`Total Leads Entered Pipeline` — count of leads submitted for scoring, regardless of whether they completed.
Source: pipeline intake log / lead creation events.

**What it tells you:**
A score coverage rate below 100% means leads are exiting the pipeline before scoring completes. These leads are invisible to all other metrics — they produce no outcomes, no actions, and no consistency data, but are not counted as failures either. They simply disappear.

**Target:**
Should be as close to 100% as operationally possible. Any sustained drop below 100% warrants investigation before trusting any other metric.

**Action if it drops:**
Check pipeline logs for unscored leads and identify at which stage they are exiting. Do not investigate scoring quality until coverage is confirmed stable.

**Owner:**
Engineering lead.

**Review cadence:**
Weekly. This is the only metric reviewed weekly — it is a pipeline health signal, not a business metric.

---

---

## Accuracy Proxy

**Question this group answers:**
Did HOT leads actually perform better than WARM, and WARM better than COLD — in real outcomes?

**Context:**
Accuracy proxy metrics validate bucket assignments against real-world outcomes. The system has no ground truth at scoring time — we cannot know whether a lead is truly HOT until the salesperson acts on it. These metrics use CRM and feedback data as a proxy for ground truth after the fact.

**Positive outcome definition:** Any one of the following qualifies as a positive outcome, treated equally — responded to outreach, meeting booked, lead qualified by salesperson, deal closed, salesperson gave thumbs up.

**Working assumption:** Operating on real bucketization output data, not a day 0 baseline.

---

### Primary Metrics

**AP1 — Bucket Outcome Rate (BOR)**

**Definition:**
For each bucket, the percentage of leads that resulted in at least one positive outcome. Calculated separately for HOT, WARM, and COLD — produces three independent values.

**Formula:**

```
Bucket Outcome Rate (HOT)  = (HOT Leads with a Positive Outcome  / Total HOT Leads)  × 100
Bucket Outcome Rate (WARM) = (WARM Leads with a Positive Outcome / Total WARM Leads) × 100
Bucket Outcome Rate (COLD) = (COLD Leads with a Positive Outcome / Total COLD Leads) × 100
```

**Variables:**

`HOT / WARM / COLD Leads with a Positive Outcome` — count of leads in that bucket where at least one of the five outcome types was recorded.
Source: CRM outcome events table and salesperson feedback log; a lead qualifies if any one outcome type appears against it, regardless of which one.

`Total HOT / WARM / COLD Leads` — count of leads assigned to that bucket.
Source: scoring output table; filter by bucket column.

**What it tells you:**
Whether each bucket is producing real results. A HOT bucket with a low outcome rate means the system is mislabeling leads as high priority.

**Target:**
TBD after Month 1 baseline. No number is set upfront.

---

**AP2 — Bucket Separation**

**Definition:**
Two things checked together from the same Bucket Outcome Rate values — whether the bucket order is correct, and whether the gap between buckets is meaningful.

**Part 1 — Order Check (pass/fail):**

```
PASS if: HOT Outcome Rate  >  WARM Outcome Rate  >  COLD Outcome Rate
FAIL if: any adjacent pair is inverted
```

No single numeric formula captures this — it is a relational check across three values. Reducing it to one number would hide which specific pair broke. The result is reported as pass with all three values shown, or fail with the inverted pair identified.

**Part 2 — Discrimination Ratio:**

```
Discrimination Ratio = HOT Outcome Rate / COLD Outcome Rate
```

**Variables:**

`HOT Outcome Rate`, `WARM Outcome Rate`, `COLD Outcome Rate` — the three values computed in AP1. No additional data required.

`Discrimination Ratio` — how many times more likely a HOT lead is to convert compared to a COLD lead. A value of 3 means HOT leads convert three times more often. A value near 1 means the system performs barely better than random assignment.

**How to report:**
Both parts reported together. A passing result states: order is correct, Discrimination Ratio = X. A failing result flags which of the two broke.

**What it tells you:**
A system can be directionally correct and practically useless at the same time. Part 1 catches mislabeling. Part 2 catches insufficient separation. Both must be read together.

**Target:**
TBD after Month 1 baseline.

---

### Diagnostic Checks

**AP3 — Completeness Qualifier**

**Definition:**
A check that within the same bucket, leads with more signals fired performed better than leads with fewer signals fired.

**Formula:**

First, compute a completeness score for each lead. Two options — the team must decide which to use:

Option A — count-based:
```
Lead Completeness Score = Signals Fired for This Lead / Total Possible Signals for This Tenant
```

Option B — weight-based:
```
Lead Completeness Score = Total Weight of Signals That Fired / Total Weight of All Possible Signals
```

Weight-based is more meaningful because a missing high-weight signal matters more than a missing low-weight one. Count-based is simpler to compute. This decision is pending from the team.

Then split each bucket into two halves at the median completeness score, and compare outcome rates:

```
PASS (per bucket):
  Outcome Rate of Above-Median Completeness Leads > Outcome Rate of Below-Median Completeness Leads
```

**Variables:**

`Signals Fired for This Lead` — count of signals that produced a value for this lead during enrichment.
Source: lineage log; count distinct signal entries per lead where status = fired.

`Total Possible Signals for This Tenant` — count of all signals defined in the tenant/persona configuration, regardless of whether they fired.
Source: persona/signal configuration table.

`Total Weight of Signals That Fired` — sum of the weight values for only the signals that fired for this lead.
Source: lineage log (which signals fired) joined with signal weight configuration table.

`Total Weight of All Possible Signals` — sum of all signal weights in the tenant configuration.
Source: signal weight configuration table.

**What failure means:**
Completeness of data is not adding new information beyond what the enrichment score already captures. Drop it from tracking.

---

### Action Rules

If AP2 order check fails: do not change signal weights yet. First audit bucket score boundaries — the boundaries are the likely cause, not the signals themselves.

If AP2 Discrimination Ratio is near 1: the scoring engine is not creating meaningful separation. Review signal selection and weights with the tenant persona team before any model changes.

If AP3 fails: remove completeness from the metric set going forward. Do not use it as a proxy for confidence.

If AP1 shows HOT Outcome Rate below 30% after baseline is established: trigger a full scoring audit — signals, weights, and persona configuration.

---

### Data Sources

Scoring output, lineage log (signals fired per lead), CRM outcome events, salesperson feedback data.

---

### Review Cadence

Monthly. Minimum 100 outcomes per bucket before any review is considered valid.

---

### Owner

AI/ML owner. Product owner co-reviews monthly.

---

---

## Consistency

**Question this group answers:**
Does the system produce the same result for the same lead, and do scores only change when something actually changes about the lead?

**Context:**
Consistency metrics validate that the scoring pipeline is stable and deterministic. A score is only useful if it means the same thing every time it is produced. Inconsistency can appear in five distinct ways — cross-run noise, temporal drift, boundary fragility, decay coherence failures, and signal calculation instability.

**Available data:** Historical score records, lineage log (signals fired, score per step, decay events, rescore events), scoring output.

---

### Primary Metrics

**C1 — Cross-Run Bucket Stability**

**Definition:**
Of leads re-scored with no data change between runs, the percentage that received the same bucket assignment in both runs.

**Formula:**

```
Bucket Stability Rate = (Leads That Got the Same Bucket in Both Runs / Total Re-scored Leads with No Data Change) × 100
```

**Variables:**

`Leads That Got the Same Bucket in Both Runs` — count of leads where the bucket from run 1 and the bucket from run 2 are identical.
Source: historical score records; join lead ID across two scoring run timestamps, filter to leads with no lineage log changes between the two runs, count where bucket matches.

`Total Re-scored Leads with No Data Change` — count of leads that were scored twice, with the lineage log confirming no new signal data, no field updates, and no manual overrides between the two runs.
Source: historical score records and lineage log.

**What it tells you:**
The core determinism check. If the same lead with the same data keeps getting different buckets, individual scores cannot be trusted — the system is noisy at the output level.

**Target:**
TBD after Month 1 baseline. Should be very high by design.

---

**C2 — Temporal Score Drift**

**Definition:**
For leads whose underlying data did not change between two time periods, how many drifted in score and by how much. Two sub-metrics tracked together.

**Sub-metric 1 — Drift Incidence Rate:**

```
Drift Incidence Rate = (Leads Whose Score Changed Despite No Data Change / Total Stable Leads) × 100
```

**Sub-metric 2 — Mean Drift Magnitude:**

```
Mean Drift Magnitude = Total Score Change Across All Drifted Leads / Count of Drifted Leads

where: Score Change per Lead = Size of the difference between Score at Period End and Score at Period Start
                               (direction of change is ignored — only the size matters)
```

**Variables:**

`Total Stable Leads` — count of leads with no data change between the two time periods.
Source: lineage log; leads where no new signals fired, no field updates, and no decay events occurred between the start and end of the measurement window.

`Leads Whose Score Changed Despite No Data Change` — count of those stable leads where the score at the end of the period differs from the score at the start.
Source: historical score records filtered to stable leads.

`Score at Period Start / Score at Period End` — the enrichment score value for each stable lead at the beginning and end of the measurement window.
Source: historical score records at the two timestamps.

`Total Score Change Across All Drifted Leads` — sum of the size of score changes (ignoring direction) across every lead that drifted.

**What it tells you:**
Drift Incidence Rate tells you how widespread the drift is. Mean Drift Magnitude tells you how severe it is. Both should be near zero for leads with no data change. Any consistent drift points to silent pipeline changes.

**Target:**
TBD after Month 1 baseline.

---

### Diagnostic Checks

**C3 — Boundary Flip Rate**

**Definition:**
Of leads sitting close to a bucket boundary, the percentage that flip to a different bucket on re-score without any data change.

**Why no formula is given now:**
The formula requires knowing where the HOT/WARM/COLD score boundaries sit in order to define which leads are "close to a boundary." Those thresholds are currently TBD. Without them, the set of leads to measure cannot be defined.

**Formula once unblocked:**

```
Boundary Flip Rate (per bucket) = (Boundary-Zone Leads That Changed Bucket on Re-score / Total Boundary-Zone Leads) × 100

where: Boundary-Zone Lead = a lead whose score falls within X points of the nearest bucket boundary
       X = danger zone width, defined once thresholds are known
```

Source of both counts: historical score records and lineage log.

**Revisit when:** Bucket score thresholds are locked.

---

**C4 — Decay-Rescore Coherence**

**Definition:**
After a decay event fires, the actual score change should match the expected decay amount. This metric measures the average gap between what decay should have done and what actually happened.

**Formula:**

```
Mean Decay Deviation = Total Gap Between Expected and Actual Score Change Across All Decay Events / Count of Decay Events

where: Gap per Decay Event = Size of the difference between Expected Score Change and Actual Score Change
                             (direction ignored — any deviation in either direction is a problem)
```

**Variables:**

`Actual Score Change per Decay Event` — the score value immediately after the decay step minus the score value immediately before it.
Source: lineage log; for each decay event entry, read the score before and after that specific step.

`Expected Score Change per Decay Event` — the score change the system's decay schedule defines for that event: −10 at 7 days, −20 at 14 days. For auto-cold events at 30 days, the expected change is whatever delta is needed to reach the COLD boundary from the lead's current score.
Source: system decay schedule configuration.

`Count of Decay Events` — total number of decay events that fired in the measurement period.
Source: lineage log; count entries where event type = decay.

`Total Gap` — sum of the per-event gaps across all decay events in the period.

**What it tells you:**
A Mean Decay Deviation of zero means decay is behaving exactly as defined. Any non-zero value means something other than decay is influencing the rescore.

---

**C5 — Signal Contribution Consistency**

**Definition:**
For any given signal with a defined weight, its contribution to the enrichment score should be identical every time it fires with the same value, regardless of which lead it is for.

**Why no tracked formula is given:**
Signal contribution consistency is a deterministic property of the code — it either computes correctly every time or it does not. There is no statistical trend to measure over time. A gradual degradation is not possible: the calculation is either right or wrong on every run. Tracking a number here would be misleading.

**How it is verified without a formula:**
At build time: a unit test confirms that the same signal, same weight, and same input value always produce the same score contribution. This runs automatically in the CI/CD pipeline on every change to the scoring logic.

Monthly spot-check from the lineage log: for any signal that fired for at least 10 leads in the period, compare the recorded score contributions across those leads for the same signal. If the same signal with the same input value produced different contributions on different leads, there is a non-determinism bug. Flag immediately.

**What failure means:**
The enrichment score calculation is not reliable. Every downstream metric is corrupted. Stop and fix before trusting any output.

---

### Action Rules

If C1 drops: do not investigate signal weights first. Check LLM temperature settings, prompt stability, and whether any non-deterministic element was introduced in the pipeline.

If C2 Drift Incidence Rate or Mean Drift Magnitude rises: check for silent changes — model version updates, signal extraction logic changes, or background jobs touching score fields. Drift without data change is always a pipeline problem, not a lead data problem.

If C3 flags many boundary flips once thresholds are defined: bucket boundaries may need widening, or a confidence buffer zone around boundaries needs to be introduced.

If C4 Mean Decay Deviation is non-zero: the rescore logic after decay is broken. The lineage log decay entries should identify exactly which step is producing the unexpected gap.

If C5 spot-check fails: stop everything. The enrichment score calculation is not reliable. Fix before trusting any other output.

---

### Data Sources

Historical score records, lineage log (signals fired per lead, score per step, decay events, rescore events), scoring output.

---

### Review Cadence

Monthly for C1 and C2. C4 checked after every decay cycle. C5 verified at build time and spot-checked monthly.

---

### Owner

AI/ML owner. Engineering lead owns C5.

---

---

## Action Relevance

**Question this group answers:**
Are salespeople acting on leads in the right order, at the right speed, with the right type of action?

**Context:**
Action relevance metrics validate that the scoring output is actually influencing salesperson behaviour. A score that is accurate and consistent but ignored by the sales team produces no business value. These metrics bridge the system output and the human response.

**Available data:** Scoring output (bucket per lead), action timestamps, action type logs, salesperson ID per action, CRM event logs, salesperson feedback.

---

### Primary Metrics

**AR1 — SLA Compliance Rate**

**Definition:**
For each bucket, the percentage of leads that were first actioned within their defined SLA window.

**Formula:**

```
SLA Compliance Rate (per bucket) = (Leads Actioned Within SLA Window / Total Leads in That Bucket) × 100

A lead is within SLA if: Time of First Action − Time of Score Assignment  ≤  SLA Window for That Bucket
```

**Variables:**

`Leads Actioned Within SLA Window` — count of leads in the bucket where the time from score assignment to first action is within the defined window.
Source: scoring output (score assignment timestamp per lead) joined with action log (earliest action timestamp per lead); apply the condition above per lead.

`Total Leads in That Bucket` — count of all leads assigned to that bucket.
Source: scoring output table.

`Time of First Action` — the timestamp of the earliest action recorded against the lead by any salesperson.
Source: action log; minimum action timestamp per lead ID.

`Time of Score Assignment` — the timestamp when the lead was assigned its bucket.
Source: scoring output.

`SLA Window for That Bucket` — the maximum allowed time between score assignment and first action.
Source: system configuration: HOT = 24 hours, COLD = 7 days. WARM window is an open decision — must be locked at either 48 hours or 72 hours before this metric can be calculated.

**What it tells you:**
Whether the system's action guidance is being followed operationally. HOT compliance is the most critical — a missed HOT lead is a missed high-priority opportunity.

**Target:**
TBD. To be set by product owner and team leads after reviewing Month 1 data.

---

**AR2 — Action Rate by Bucket**

**Definition:**
Of all leads in each bucket, the percentage that received any action at all.

**Formula:**

```
Action Rate (per bucket) = (Leads That Received at Least One Action / Total Leads in That Bucket) × 100
```

**Monotonicity check:**

```
PASS if: HOT Action Rate  >  WARM Action Rate  >  COLD Action Rate
FAIL if: any adjacent pair is inverted
```

Same reasoning as AP2 Part 1 — a relational check across three values. Reducing it to one number loses which pair failed.

**Variables:**

`Leads That Received at Least One Action` — count of leads in the bucket that appear at least once in the action log.
Source: action log joined with scoring output; count distinct lead IDs per bucket with at least one action entry.

`Total Leads in That Bucket` — count of all leads assigned to that bucket.
Source: scoring output table.

**What it tells you:**
Whether salespeople are using the score to prioritise. A monotonicity violation means the scoring output is not influencing behaviour — this is a system adoption problem, not a scoring accuracy problem.

**Target:**
TBD after Month 1 baseline.

---

### Diagnostic Checks

**AR3 — Time-to-Action Distribution**

**Definition:**
For each bucket, the distribution of time elapsed between score assignment and first action across all actioned leads.

**Why no single formula is given:**
A distribution cannot be meaningfully reduced to one number without losing the diagnostic value. The shape — whether times are tightly clustered or have a long tail — is what identifies the problem. A single average would hide a situation where some leads are actioned in 1 hour and others in 50 hours, both averaging within SLA but reflecting broken prioritisation in practice.

**How it is calculated:**
Compute per-lead time-to-action first:

```
Time-to-Action per Lead = Time of First Action − Time of Score Assignment
```

Source of both values: same as AR1.

Then for each bucket report three aggregates: Mean Time-to-Action, Median Time-to-Action, and 90th Percentile Time-to-Action. The 90th percentile is the most useful — it captures the tail where SLA breaches and delayed leads concentrate.

---

**AR4 — Action Type Distribution by Bucket**

**Definition:**
For each bucket, the percentage breakdown of action types taken — calls, emails, meetings, etc.

**Why no single pass/fail formula is given:**
There is no universal standard for what action type mix is "correct" for each bucket. The expected distribution depends on team norms, tools available, and the tenant's sales process. Hardcoding those norms into a formula at this stage is not appropriate.

**How it is calculated:**
For each bucket and each action type:

```
Action Type Share = (Leads in Bucket Actioned with This Action Type / Total Actioned Leads in Bucket) × 100
```

Source: action type log (action type per event) joined with scoring output (bucket per lead).

Report as a side-by-side breakdown per bucket. The team reviews whether HOT is receiving predominantly higher-intensity actions (calls, meetings) compared to WARM and COLD. What counts as higher intensity is defined by the team based on available action types.

---

**AR5 — Salesperson Priority Alignment**

**Definition:**
For each salesperson, the percentage of working sessions in which they actioned the highest-available bucket lead first.

**Formula:**

```
Salesperson Priority Alignment = (Sessions Where Highest-Bucket Lead Was Actioned First / Total Sessions with Leads from Multiple Buckets Available) × 100
```

**Variables:**

`Sessions Where Highest-Bucket Lead Was Actioned First` — count of sessions where the first lead the salesperson acted on belonged to the highest bucket available to them in that session.
Source: action log (first action per session per salesperson) joined with scoring output (bucket per lead).

`Total Sessions with Leads from Multiple Buckets Available` — count of working sessions where the salesperson had at least one lead from two or more different buckets available to action.
Source: action log and scoring output, grouped by salesperson ID and session window.

`Session` — a defined time window representing one working period for a salesperson. Must be agreed by the team before this metric can be calculated. Recommended starting point: one calendar day per salesperson.

**What it tells you:**
Low alignment for specific individuals is a coaching signal. Low alignment systemically across all salespeople is a UX signal — the interface is not making priorities visible enough.

---

### Action Rules

If AR1 shows HOT compliance dropping: check whether the team lead SLA breach alert is firing correctly. If it is and compliance is still low, the problem is workload capacity, not system failure.

If AR2 shows low action rate for HOT: investigate whether scores are visible in the workflow before questioning the scores themselves.

If AR3 shows a long tail for HOT: leads are being queued and worked in batches instead of continuously. This is a workflow and prioritisation problem.

If AR4 shows action type mismatch: raise with product owner — this is a UI and training issue, not a scoring issue.

If AR5 shows low alignment for specific salespeople: flag for team lead review. If systemic across all salespeople, review how scores are surfaced in the interface.

---

### Data Sources

Scoring output, action timestamps, action type logs, salesperson ID per action, CRM event logs.

---

### Review Cadence

Monthly for AR1 and AR2. AR3 and AR4 reviewed quarterly or when AR1/AR2 flag a problem. AR5 reviewed monthly and shared with team leads.

---

### Owner

Product owner. Team leads own AR5 follow-through.

---

---

## Global KPIs

**What this section is for:**
The sections above each cover one specific part of the scoring system. This section rolls everything up into three numbers for the dashboard — one view that tells you how the system is doing across all tenants without having to read each group separately.

---

### Global KPI 1 — System Health

**Question this answers:**
Is the scoring system running properly across all tenants — are leads making it through, and are scores coming out the same way every time?

**Two numbers shown side by side:**

```
Pipeline Coverage   =   Average Scaore Coverage Rate across all tenants
Score Stability     =   Average Bucket Stability Rate across all tenants
```

Both are percentages. Both should be high. If either drops, something is broken in the pipeline — not in the scoring logic, but in the engine itself.

**How to read it at a glance:**
- Both near 100% → system is running cleanly
- Coverage drops → leads are getting lost before scoring even happens
- Stability drops → the same lead is getting different scores on different runs — the output cannot be trusted

**These are not combined into one number.** A 60% coverage and 100% stability would average to 80% and look fine — but 40% of leads being lost is not fine. Showing them separately means nothing can hide.

**Data comes from:** Score Coverage Rate (pipeline intake log) and C1 Bucket Stability Rate (historical score records). Both already calculated in the sections above.

**Owner:** Engineering lead.

**Review cadence:** Weekly. Any drop here takes priority over everything else.

---

### Global KPI 2 — Business Health

**Question this answers:**
Is the scoring actually helping the sales team — are HOT leads clearly better than COLD leads, and are salespeople acting on them in time?

**Two numbers shown side by side:**

```
Scoring Lift        =   Median Discrimination Ratio across all tenants
HOT Response Rate   =   Average HOT SLA Compliance Rate across all tenants
```

**Scoring Lift** tells you how much better HOT leads are performing compared to COLD leads, averaged across all tenants. A value of 3 means HOT leads are converting 3 times more often than COLD. A value near 1 means scoring is not making any difference.

**HOT Response Rate** tells you what percentage of HOT leads across all tenants are being followed up within the required time window. A HOT lead that no one acts on fast enough is a wasted opportunity.

**How to read it at a glance:**
- Scoring Lift is high, HOT Response Rate is high → scoring is working and the team is using it
- Scoring Lift is low → the scoring logic needs review — it is not separating good leads from bad ones
- HOT Response Rate is low → the sales team is not acting fast enough — this is a workflow or training problem, not a scoring problem

**These are not combined into one number** for the same reason as above — a broken lift score and a perfect response rate would cancel each other out and hide the real issue.

**Data comes from:** AP2 Discrimination Ratio (CRM outcomes) and AR1 HOT SLA Compliance Rate (action logs). Both already calculated in the sections above.

**Owner:** Product owner. AI/ML owner co-reviews Scoring Lift.

**Review cadence:** Monthly.

---

### Global KPI 3 — Tenant Health Rate

**Question this answers:**
What percentage of tenants are fully healthy right now — meaning all their primary metrics are within the acceptable range?

**Formula:**

```
Tenant Health Rate = (Tenants Where All Primary Metrics Are Within Range / Total Active Tenants) × 100
```

**How to read it at a glance:**
- 100% → every tenant is healthy
- Drops to 94% → 6 tenants need attention — drill down to per-tenant view to see which ones and which metric is failing

This is the one number an executive can look at. When it drops, the team investigates which tenants are pulling it down and why.

**Why this is not available yet:**
This metric requires thresholds — a defined range for what "within acceptable" means for each primary metric. Those thresholds cannot be set until Month 1 baseline data exists. Until then, this slot on the dashboard remains blank.

**What triggers it being turned on:** Once Month 1 data is in, the team sets thresholds for Coverage Rate, Bucket Stability, Discrimination Ratio, and HOT SLA Compliance per tenant. After that, this metric is live.

**Owner:** Product owner.

**Review cadence:** Monthly once live.

---

### Summary View

| Global KPI | What It Shows | Numbers Inside |
|---|---|---|
| System Health | Is the engine running correctly? | Pipeline Coverage + Score Stability |
| Business Health | Is scoring creating value? | Scoring Lift + HOT Response Rate |
| Tenant Health Rate | What % of tenants are fully healthy? | Single % (live after Month 1 baseline) |
