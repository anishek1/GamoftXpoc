---
type: analysis
question: "Define measurable product KPIs for the Lead Intelligence Engine — scoring quality, accuracy proxy, consistency, and action relevance metrics"
date: 2026-04-14
tags: [kpi, metrics, planning, scoring-quality, accuracy, consistency, action-relevance]
sources_consulted: [sources/2026-lead-intelligence-engine-reference]
related_concepts: [confidence-first-class, feedback-loop, lineage-log, score-decay, action-sla, disqualification-gate, persona-layer, lead-pipeline-architecture]
---

# Success Metrics Framework — Lead Intelligence Engine

**Question:** Create measurable product KPIs for planning and future validation. Define scoring quality, accuracy proxy, consistency, and action relevance metrics.  
**Date:** 2026-04-14  
**Status:** Discussion artifact — not committed. 8 open decisions in Section 7.

---

## 1. First Principles

### 1.1 Reframe the System's Job

The system's job is **not** "to score leads accurately." That is a means. The job is to **shift salesperson time allocation toward leads that convert, with enough explainability that salespeople trust the shift.**

This reframe exposes three measurement traps.

### 1.2 The Three Measurement Traps

**Trap 1 — Counterfactual**

The problem is that we can only observe outcomes of leads that were actually called. We cannot measure missed conversions sitting in the COLD bucket. This means true recall is unmeasurable by default — we never know what we missed.

The mitigation is the **Curiosity Budget**: mandate calling 5% of COLD leads every week. Their conversion rate then becomes the COLD baseline, giving us a window into what the system is quietly ignoring.

**Trap 2 — Attribution**

The problem is that when a HOT lead converts, the credit goes simultaneously to the score, the salesperson, the product, and plain luck. There is no clean way to isolate any one factor.

The mitigation is **per-salesperson lift**: compare each salesperson's conversion rate before and after launch, intra-user. This isolates the system's impact from the salesperson's inherent skill level.

**Trap 3 — One-Number Accuracy**

The problem is that the word "accuracy" collapses four independent failure modes — bucket assignment, explanation quality, confidence calibration, and action relevance — into a single number that hides where exactly things go wrong.

The mitigation is to **decompose into 4 dimensions** and assign separate metrics to each failure mode, so we know which specific thing broke when something goes wrong.

### 1.3 Terminology

**Tier** — A hierarchy layer numbered 0 through 3 that determines who reviews the metric, how often they review it, and what action they are expected to take when something moves.

**Target** — A threshold that defines "good enough." There are four types: hard (pass/fail — below this is a bug), soft (directional — ramps with system maturity), alert threshold (a floor below which the system is considered broken), and ratio (a relative comparison that is less sensitive to noise).

**Availability** — The earliest date at which a metric can be measured in a meaningful way. Expressed as Day 0, Week N, or Month N.

**Curiosity Budget** — A mandated practice of sampling 5% of COLD bucket leads for calling every week. This is the only structural mechanism that makes COLD baseline conversion measurable.

**Shadow re-run** — An independent re-execution of Agent E using a different LLM provider, used for cross-validation of scores.

---

## 2. Tier Hierarchy

**Tier 0 — North Star**

Reviewed by Leadership and tenant admins on a quarterly cadence. Contains only 1 to 3 metrics in total across the entire system. These metrics define whether the product is succeeding at its real job — not its intermediate job, but its ultimate purpose.

**Tier 1 — Health Scorecard**

Reviewed by the product owner and team lead on a weekly cadence. Contains no more than 7 metrics per tenant. These are the leading indicators for Tier 0 and form the main operational dashboard the team watches.

**Tier 2 — Diagnostic**

Reviewed by engineers and analysts on demand — meaning only when a Tier 1 metric moves unexpectedly. The number of metrics here is unbounded. The purpose is to answer the question "why did that move?" rather than to monitor health.

**Tier 3 — Infrastructure**

Reviewed by the engineering team daily or via automated alerts. Also unbounded in count. Covers cost, latency, log integrity, and data isolation — the foundational hygiene without which nothing else is reliable.

---

## 3. Target Types

**Hard Target**

This is a pass/fail threshold. Falling below it means there is a bug, not a performance issue. An example is "100% of leads must be logged with `prompt_version`" — anything less than 100% is a defect to be fixed immediately.

**Soft Target**

This is a directional target that is expected to ramp up as the system matures. It is not a bug if you miss it early, but you must be trending toward it. An example is ">70% SLA compliance in Month 1, rising to >85% by Month 3."

**Alert Threshold**

This is a floor. Falling below it means the system is considered broken, not just underperforming. An example is "<20% feedback rate triggers an alert" — this threshold is locked and does not soften with time.

**Ratio Target**

This is a relative comparison between two rates rather than an absolute number. It is less sensitive to noise because both sides of the ratio move together in a well-functioning system. An example is "HOT:COLD conversion must be at least 2.5 times."

Every target — regardless of type — is conditional on three things: a minimum sample size of N≥30 by default, a per-tenant baseline rather than a global average, and the current maturity stage of the system.

---

## 4. Full Metrics Catalog

### 4.1 Dimension A — Scoring Quality

*This dimension answers: is Agent E producing meaningful, differentiated scores?*

---

**A1 — Bucket–Outcome Alignment Rate**
Tier 1

**Definition:** The percentage of called leads whose confirmed real-world outcome matched the bucket they were assigned. HOT leads should convert or progress. WARM leads should engage. COLD leads should go nowhere.

**Target:** Soft — above 75% after calibration.

**Available from:** Month 2 onwards.

**How it can mislead you:** This metric only reflects leads that were actually called. COLD leads are entirely unmeasured unless the Curiosity Budget is active. Without it, the metric looks complete but is structurally blind on one side.

---

**A2 — HOT:COLD Conversion Ratio**
Tier 0 (North Star)

**Definition:** The conversion rate of HOT leads that were called, divided by the conversion rate of COLD leads that were called via the Curiosity Budget. This ratio tells you whether the scoring has real signal — whether being marked HOT actually means something.

**Target:** Ratio — at least 2.5 times.

**Available from:** Month 3 onwards.

**How it can mislead you:** If the Curiosity Budget sample is small, the confidence interval around the COLD conversion rate will be very wide and the ratio will be unreliable. You need at least 30 called COLD leads per tenant per quarter before this number is trustworthy.

---

**A3 — Dimensional Differentiation Index**
Tier 2

**Definition:** The mean standard deviation across the 5 Agent E sub-scores — Fit, Intent, Engagement, Behavioral, and Context — measured on a 10-point scale. This checks whether Agent E is actually spreading scores out or clustering them at the same value.

**Target:** Soft — standard deviation of at least 1.5 on a 10-point scale.

**Available from:** Day 0.

**How it can mislead you:** The LLM may produce artificial variance that looks mathematically spread but is not semantically meaningful. Cross-check against A4 to see if the differentiation holds across different tenants.

---

**A4 — Cross-Tenant Divergence**
Tier 2

**Definition:** A set of identical synthetic test leads run through all 3 tenants. The metric measures what percentage of those leads produce a different bucket in at least 2 of the 3 tenants. This validates that different personas actually produce different scoring behaviour.

**Target:** Soft — at least 60% divergence.

**Available from:** Day 0, but requires a test harness to be built first.

**How it can mislead you:** If the test corpus is too generic or too extreme, it will produce artificial results. The leads used must probe the actual differences between personas carefully, not just edge cases that would flip under any reasonable configuration.

---

**A5 — Wrong-Bucket Rate (Directional)**
Tier 1

**Definition:** This metric is split into two halves. The first is the **false alarm rate** — HOT leads that should have been COLD. The second is the **missed opportunity rate** — COLD leads that should have been HOT. Keeping these two separate matters because they have different costs and different causes.

**Target:** Soft — false alarm below 15%; missed opportunity below 10%.

**Available from:** Week 4 onwards.

**How it can mislead you:** Missed opportunities are silent. They only become visible if the Curiosity Budget is active. Without it, the missed opportunity half of this metric is structurally unobservable.

---

### 4.2 Dimension B — Accuracy Proxy

*This dimension answers: before conversion data arrives, can we detect quality issues?*

---

**B1 — Confidence Calibration Error (ECE)**
Tier 1

**Definition:** The weighted average of the absolute difference between Agent E's predicted confidence and the actual observed outcome rate, across confidence bins. Plotted as a reliability diagram, this shows whether the system's confidence is honest — if it says 80% confident, does it convert at 80%?

**Target:** Soft — ECE below 0.10, meaning the reliability diagram line stays within ±10% of the perfect diagonal.

**Available from:** Month 2 onwards.

**How it can mislead you:** Small sample sizes in high-confidence bins make the error noisy and hard to interpret. You need at least 100 resolved leads per tenant before the diagram becomes trustworthy.

---

**B2 — Confidence Distribution Shape**
Tier 1

**Definition:** The percentage of leads falling into each confidence band — high confidence at 80% and above, mid at 50–79%, and low below 50% — measured per tenant. This tells you whether the system is making real distinctions or defaulting to uncertainty.

**Target:** Soft — less than 30% of leads in the low-confidence band; more than 50% in the high-confidence band after calibration.

**Available from:** Day 0.

**How it can mislead you:** LLMs tend to self-report confidence in round numbers, clustering at exactly 80%. Look at the shape of the distribution rather than the averages — the clustering pattern itself is diagnostic.

---

**B3 — Completeness Tier Mix**
Tier 2

**Definition:** The percentage of leads reaching Agent E classified as Complete, Partial, or Sparse by Agent C. This tells you the quality of the input data Agent E is working with.

**Target:** Soft — more than 60% Complete; fewer than 20% Sparse.

**Available from:** Day 0.

**How it can mislead you:** "Complete" in this context means field presence, not truthfulness. A lead with a wrong phone number but all fields filled still looks Complete to this metric. Data quality is confirmed structurally, not semantically.

---

**B4 — Explanation–Outcome Decoupling**
Tier 2

**Definition:** For leads that actually converted, this checks whether the salesperson's stated reason for conversion matches any of Agent E's three key reasons given in the explanation. It tests whether the system's explanations are actually connected to reality or are post-hoc rationalizations.

**Target:** Soft — at least 50% match.

**Available from:** Month 2 onwards.

**How it can mislead you:** There is a strong post-hoc rationalization risk. The salesperson's stated reason must be captured *before* they see Agent E's reasons, otherwise they will unconsciously align their answer to the system's explanation.

---

**B5 — Shadow Re-run Disagreement Rate**
Tier 2

**Definition:** 2 to 5% of leads are re-run through a second LLM from a different provider. The metric measures what percentage of those re-runs produce a different bucket than the original run.

**Target:** Soft — below 20% disagreement; an alert fires if it sustains above 30%.

**Available from:** Day 0 if shadow infrastructure is shipped; otherwise Month 2.

**How it can mislead you:** Two different models can agree on the same wrong answer for different reasons. This metric should be triangulated with human reviewer audits, not treated as a standalone accuracy signal.

---

### 4.3 Dimension C — Consistency

*This dimension answers: is the system stable and predictable enough to trust?*

---

**C1 — Cross-Run Variance**
Tier 1

**Definition:** The same lead is submitted twice with the same prompt version. The metric measures the score delta between the two runs. The bucket must never flip between runs.

**Target:** Hard — bucket never flips. Soft — score variance of no more than 5 points, 95% of the time.

**Available from:** Day 0.

**How it can mislead you:** LLM provider non-determinism — especially batching quirks at T=0 — can cause variance that reflects the provider's infrastructure rather than the system's design. Early results measure provider stability as much as system stability.

---

**C2 — Prompt Version Logged**
Tier 3

**Definition:** The percentage of leads that have a non-null `prompt_version` field in the lineage log. This is a hygiene metric that makes every other consistency metric interpretable — if you don't know which prompt version scored a lead, you can't diagnose regressions.

**Target:** Hard — 100%.

**Available from:** Day 0.

**How it can mislead you:** Auto-population logic can make this metric look 100% while actually writing incorrect or stale prompt versions. Audit occasionally by comparing the logged value against the actual prompt hash.

---

**C3 — Distribution Drift Detection**
Tier 1

**Definition:** Week-over-week KL divergence of the bucket distribution per tenant. This detects when the overall shape of how leads are being scored shifts significantly, without any intentional change to prompts, personas, or data sources.

**Target:** Alert threshold — KL divergence above 0.15 with no corresponding prompt, persona, or source change should trigger an investigation.

**Available from:** Week 2 onwards.

**How it can mislead you:** In the early months, normal seasonality in lead data can look indistinguishable from drift. Use noise-aware thresholds that account for expected variation. This metric is particularly valuable for catching silent model updates pushed by the LLM provider.

---

**C4 — Baseline Anchor Test**
Tier 3

**Definition:** 10 canonical test leads run through production every day. Their scores and buckets are compared against their historical distribution. If they move, something in the system has changed — intentionally or not.

**Target:** Hard — all 10 leads must stay within tolerance.

**Available from:** Day 0.

**How it can mislead you:** The anchor corpus must be maintained and refreshed. A stale corpus — leads that no longer represent the real distribution of inputs — produces a stale signal that misses genuine regressions while giving a false sense of stability.

---

**C5 — Decay Determinism**
Tier 3

**Definition:** Score changes for inactive leads must match the locked decay formula exactly, with zero exceptions.

**Target:** Hard — 100% match.

**Available from:** Day 30 onwards.

**How it can mislead you:** If the decay calculation and feedback-based adjustments operate on the same score field, deviations from the expected decay may be caused by feedback logic rather than a decay bug. Log each mechanism in a separate field so deviations can be diagnosed correctly.

---

### 4.4 Dimension D — Action Relevance

*This dimension answers: is the scoring actually changing salesperson behavior?*

---

**D1 — HOT SLA Compliance Rate**
Tier 1

**Definition:** The percentage of HOT leads that were contacted within 24 hours of being assigned. This measures whether the urgency signal embedded in HOT classification is actually translating into faster response.

**Target:** Soft — above 70% in Month 1; above 85% from Month 3 onwards.

**Available from:** Day 0.

**How it can mislead you:** "Contacted" may be auto-logged by a CRM action without genuine human contact occurring. Audit a sample of contact records to verify the content was real outreach, not a system-generated log entry.

---

**D2 — Action Distribution Ratio**
Tier 1

**Definition:** The call rate for HOT leads divided by the call rate for COLD leads. This is the hardest available signal that scoring is actually influencing how salespeople allocate their time, rather than being politely acknowledged and then ignored.

**Target:** Ratio — at least 3:1.

**Available from:** Day 0 onwards.

**How it can mislead you:** This metric does not distinguish between scoring driving the behavior change or pre-existing salesperson intuition aligning with the score. Use alongside D5 for a fuller picture.

---

**D3 — Feedback Rate and Quality**
Tier 1

**Definition:** This metric has two parts. Part A is the percentage of leads that received any feedback tag from a salesperson. Part B is the percentage of verdicts that included a reason tag, not just a thumbs-up or thumbs-down. Both parts matter — volume tells you the system is being used, and reason tags tell you the feedback is informative.

**Target:** Part A — alert threshold below 20%; soft target above 40%. Part B — soft target above 60%.

**Available from:** Week 1 onwards.

**How it can mislead you:** High feedback volume can be driven by habit-clicking — salespeople reflexively tagging everything without genuine evaluation. Catch this by monitoring how low the reason-tag rate is and by conducting periodic reviewer audits.

---

**D4 — Suggested Action Acceptance**
Tier 2

**Definition:** The percentage of leads where the salesperson took the specific action that Agent E suggested — whether that was a call, a WhatsApp message, an email, or a nurture sequence.

**Target:** Soft — above 50%. If it drops below 20%, the suggested action feature should be reconsidered.

**Available from:** Month 1 onwards.

**How it can mislead you:** High acceptance may simply reflect the fact that salespeople default to whichever action is easiest or most habitual, regardless of what Agent E recommended. The metric cannot distinguish genuine acceptance from coincidental alignment.

---

**D5 — Per-Salesperson Conversion Lift**
Tier 0 (North Star)

**Definition:** Each salesperson's conversion rate compared before and after launch. The goal is to see a measurable positive shift in the median salesperson, with no regression in the bottom quartile.

**Target:** Soft — median lift of at least +20%; bottom quartile must stay non-negative.

**Available from:** Month 3 onwards.

**How it can mislead you:** This metric is heavily confounded by market changes, team growth, seasonality, and individual skill development that happen to coincide with launch. Mitigate by using rolling cohort analysis rather than a single pre/post comparison.

---

### 4.5 Dimension M — Meta Metrics

*If these metrics break, everything above becomes unreliable.*

---

**M1 — Lineage Log Completeness**
Tier 3

**Definition:** The percentage of leads with complete per-step lineage entries in the log. This is a non-negotiable hard dependency. Without full lineage, no other metric can be diagnosed when it moves unexpectedly.

**Target:** Hard — 100%.

**Available from:** Day 0.

---

**M2 — Feedback Honesty Audit**
Tier 3

**Definition:** A quarterly human review that checks whether the feedback tags applied by salespeople actually align with the CRM-recorded outcomes for those leads. This tests whether the feedback signal the system is receiving is honest or systematically biased.

**Target:** Soft — at least 85% alignment.

**Available from:** Month 2 onwards.

---

**M3 — Reviewer Agreement Ceiling**
Tier 2

**Definition:** The rate at which human reviewers agree with Agent E's bucket assignment. Counterintuitively, this metric is an alert when the agreement rate is *too high* — above 95% is a signal that reviewers are rubber-stamping rather than genuinely evaluating.

**Target:** Alert threshold — above 95% is a red flag.

**Available from:** Month 1 onwards.

---

**M4 — Sample-Size Sufficiency Flag**
Tier 3

**Definition:** Every metric must report its confidence interval alongside its value. Any metric whose sample size falls below N=30 is automatically marked "insufficient data" and must not trigger alerts until the threshold is crossed.

**Target:** Hard — no alerts fire below the N threshold.

**Available from:** Day 0.

---

**M5 — Tenant Data Isolation Audit**
Tier 3

**Definition:** A check for any cross-tenant signal leakage — any case where data from one tenant's leads influences the scoring of another tenant's leads.

**Target:** Hard — zero instances.

**Available from:** Day 0.

---

**M6 — PII Retention Compliance**
Tier 3

**Definition:** The percentage of log entries that are past their retention window and have been correctly scrubbed of personally identifiable information.

**Target:** Hard — 100%.

**Available from:** Month 1 onwards.

---

## 5. Edge Case Catalogue

### 5.1 Cold Start

**Scenario 1 — New tenant with no history**

When a new tenant is onboarded with no prior conversion history, the relative lift metrics — especially D5 — cannot be calculated for at least 90 days. The mitigation is to use absolute targets first, such as "HOT leads account for at least X% of the book." Switch to relative targets only after the baseline stabilises.

**Scenario 2 — New source channel activated mid-quarter**

Adding a new lead source mid-quarter pollutes distribution trend metrics because the new channel's behaviour is mixed into the existing trend. The mitigation is to tag all metrics with `source_activated_at` and exclude the first two weeks of data from that source from any trend calculations.

**Scenario 3 — Persona update mid-period**

When a persona is updated, it creates a performance discontinuity in the time series. Every metric must include `persona_version` as a field. When a persona changes, the series must be explicitly broken — never smooth across a persona change as if it is continuous data.

### 5.2 Feedback Reliability

**Scenario 4 — Salesperson marks everything "wrong bucket" out of frustration**

This creates a false negative spike in feedback quality. Detect this with a per-user verdict diversity metric. Any user where more than 80% of their verdicts carry the same tag should be flagged for an audit.

**Scenario 5 — Salesperson marks everything "converted" due to perverse incentive**

This inflates apparent accuracy. Cross-check all feedback-based accuracy metrics against CRM conversion records as the authoritative source.

**Scenario 6 — Two salespeople disagree on the same lead**

This produces an ambiguous verdict. A policy decision is required (see Section 7, Decision 5): either most-recent-wins, highest-role-wins, or store both. One option must be chosen and documented in the schema before launch.

**Scenario 7 — One heavy user dominates feedback volume**

This skews per-tenant aggregate metrics toward that user's patterns. Mitigate by capping each individual user's contribution to the aggregate metric at a defined percentage.

### 5.3 Sales Cycle Length

**Scenario 8 — Gamoft B2B cycles of 90–180 days**

The question "did this HOT lead convert?" cannot be answered for 6 months, which makes standard conversion metrics useless in the short term. The mitigation is to define milestone-based proxy outcomes — meeting booked, proposal submitted, contract signed — where each milestone counts as a mini-conversion for metric purposes.

**Scenario 9 — Urvee B2C cycles of hours**

HOT leads for Urvee should convert the same day. The SLA framework is implicitly tenant-dependent and must be configured separately per tenant, not treated as a single universal setting.

### 5.4 LLM Behaviour

**Scenario 10 — Malformed JSON from Agent E**

When Agent E returns malformed output, the lead has no bucket and cannot be scored. The mitigation is an explicit `agent_error` status. Track the rate of this status. The hard target is below 1%.

**Scenario 11 — Agent E hallucinates a signal**

A fabricated explanation leads to a wrong action recommendation. Mitigate by auditing 5% of explanations against the raw source data. Escalate to engineering review if the hallucination rate exceeds 5%.

**Scenario 12 — Token limit truncation**

When the input to Agent E approaches the token limit, context is silently dropped. Log the input token count for every lead. Correlate near-limit leads with outcome quality to determine whether truncation is causing degraded accuracy.

**Scenario 13 — Provider silently updates their model**

The LLM provider may update the underlying model without notice, causing score behaviour to shift without any change on our side. The Baseline Anchor Test (C4) is the primary mechanism for detecting this.

**Scenario 14 — T=0 non-determinism**

The same input submitted at the same time may produce slightly different scores due to LLM sampling randomness. The Cross-Run Variance metric (C1) alerts when this produces a bucket flip.

### 5.5 Operational

**Scenario 15 — Rate limit exhausted mid-run**

When a pipeline run is interrupted by rate limiting, partial results should be placed in a separate `incomplete_fetch` bucket. Never average incomplete results into clean runs — the two populations are not comparable.

**Scenario 16 — API auth token expired**

A halted pipeline produces no results. Track pipeline completion rate as an explicit metric and alert on halts immediately.

**Scenario 17 — Deduplication merged two distinct people sharing a phone number**

If two different people were merged into one lead record, the scoring is applied to the wrong person. Add a feedback option for salespeople to flag "this isn't the expected person" and route those flags to a dedup audit queue.

### 5.6 Statistical

**Scenario 18 — Simpson's Paradox**

A metric can look good at the global level while being bad for every individual tenant, if the tenant mix is skewed. The rule is: never report global metrics without per-tenant breakdowns and cross-tenant variance alongside them.

**Scenario 19 — Small-sample false alarms**

With small sample sizes, random variation produces alerts for metrics that are actually healthy. Use Wilson confidence intervals for all proportions. Suppress alerts automatically below N=30.

**Scenario 20 — Multiple-testing fallacy**

With 30 KPIs, statistical chance alone will produce roughly 1.5 false alarms per week at a 5% significance level. Apply Bonferroni correction, or explicitly accept higher per-metric thresholds to account for multiple comparisons.

### 5.7 Adversarial

**Scenario 21 — Lead source poisoning**

A compromised or manipulated lead source can skew metrics in a way that looks like system improvement. Apply anomaly detection on source volume to catch unusual spikes in lead quantity from a single source.

**Scenario 22 — Reviewer rubber-stamping**

If reviewers agree with Agent E reflexively rather than genuinely, the M3 reviewer agreement metric becomes meaningless. Inject occasional synthetic leads where Agent E is known to be wrong. Reviewers should catch these injections.

**Scenario 23 — Tenant admin gaming the persona**

A tenant admin could artificially inflate HOT counts by making the persona extremely permissive. Mitigate by rate-limiting persona updates and auditing all persona changes for unusual bucket distribution shifts.

### 5.8 Causal

**Scenario 24 — "Would have converted anyway"**

The system may receive credit for conversions that would have happened without it. Build comparison infrastructure early — either an A/B hold-out group or a propensity-matched pre/post comparison.

**Scenario 25 — Salesperson skill drift**

Salespeople improve over time independently of the system. If you compare against a single pre-launch baseline, this improvement gets attributed to the system. Use rolling quarterly baselines so the comparison window stays current.

---

## 6. Temporal Rollout Plan

*When each metric becomes meaningfully measurable.*

**Day 0 — POC Launch**

The following metrics are available from the moment the system goes live: A3 (Dimensional Differentiation Index), A4 (Cross-Tenant Divergence, if the test harness is built), B2 (Confidence Distribution Shape), B3 (Completeness Tier Mix), C1 (Cross-Run Variance), C2 (Prompt Version Logged), C4 (Baseline Anchor Test), C5 (Decay Determinism), D1 (HOT SLA Compliance Rate), D2 (Action Distribution Ratio), M1 (Lineage Log Completeness), M4 (Sample-Size Sufficiency Flag), and M5 (Tenant Data Isolation Audit).

**Week 1 to Week 4**

As early feedback data accumulates, the following become available: A5 (Wrong-Bucket Rate, directional), B5 (Shadow Re-run Disagreement Rate, if shadow infrastructure is shipped), C3 (Distribution Drift Detection), D3 (Feedback Rate and Quality), and D4 (Suggested Action Acceptance).

**Month 2 to Month 3**

With enough resolved leads to calculate calibration and lift: A1 (Bucket–Outcome Alignment Rate), B1 (Confidence Calibration Error), B4 (Explanation–Outcome Decoupling), D5 (Per-Salesperson Conversion Lift — requires pre-launch baseline to have been captured), M2 (Feedback Honesty Audit), M3 (Reviewer Agreement Ceiling), and M6 (PII Retention Compliance).

**Month 3 and beyond**

A2 (HOT:COLD Conversion Ratio) — this is the Tier 0 North Star metric and requires the Curiosity Budget to have been running for at least a full quarter to produce a reliable COLD baseline.

**Month 6 and beyond — post-adaptive layer**

Signal-level integrity metrics from the deferred [[concepts/adaptive-signal-lifecycle]] become relevant only once the adaptive layer is built.

---

## 7. Decisions Required

*These are blockers. Each should be resolved in a dedicated ticket before launch.*

**Decision 1 — Confidence Calculation Method**

The choice is between self-report from the LLM, completeness-based scoring from Agent C, or a hybrid of both.

This affects: B1, B2, and all confidence-routing logic.

Recommendation: Use the hybrid. Set `confidence = min(signal_completeness, llm_self_reported)`. The completeness score provides the floor based on data quality. The LLM self-report provides the ceiling. Neither alone is sufficient.

---

**Decision 2 — Curiosity Budget Adoption**

Should we mandate calling 5% of COLD leads every week?

This affects: A2 (North Star) and the missed-opportunity half of A5.

Recommendation: Strong yes. Without the Curiosity Budget, the entire accuracy story is structurally blind on the COLD side. This is the cheapest item on the list — it costs only salesperson time, not engineering effort.

---

**Decision 3 — Pre-Launch Baseline Capture**

Should we capture a per-salesperson, per-tenant conversion baseline covering at least 30 days before launch?

This affects: D5 (North Star).

Recommendation: Yes, mandatory. If this is skipped, reliable lift measurement is never possible — there is no way to retroactively construct the baseline after launch.

---

**Decision 4 — Per-Tenant Reporting Discipline**

Should global metrics be locked out in favour of always showing per-tenant breakdowns?

This affects: all metrics.

Recommendation: Lock this as a rule. The dashboard template should enforce it structurally so that global-only views are not possible by default.

---

**Decision 5 — Canonical Verdict on Salesperson Disagreement**

When two salespeople give conflicting feedback on the same lead, which verdict wins?

This affects: all feedback-based metrics.

Options are most-recent-wins, highest-role-wins, or store both verdicts separately. One option must be chosen before launch and documented in the schema.

---

**Decision 6 — Shadow Re-run Budget**

Is the approximately 5% increase in LLM costs from running shadow re-runs worth the cross-validation signal?

This affects: B5.

Recommendation: Defer to Month 3 unless silent failure is considered high-priority. Start without it. Add it only if A1 or A5 indicate quality problems that need a second opinion.

---

**Decision 7 — Milestone-Based Proxy Outcomes for Gamoft**

Gamoft's B2B sales cycles of 90–180 days make standard conversion metrics unmeasurable in the short term. Should we define milestone proxies?

This affects: A1, A2 specifically for the Gamoft tenant.

Recommendation: Yes. Define 3 to 4 milestones for Gamoft — for example, meeting booked, proposal sent, contract signed. Urvee's short B2C cycles likely do not need this.

---

**Decision 8 — Test Harness Corpus Ownership**

Who owns the canonical test corpus used by C4 and A4, and who is responsible for refreshing it quarterly?

This affects: C4 (Baseline Anchor Test) and A4 (Cross-Tenant Divergence).

Recommendation: Assign a single named owner before launch. Without ownership, anchor tests will rot and begin producing stale, misleading stability signals.

---

## 8. Minimum Viable Scorecard

*If the full framework is overwhelming, these are the 7 Tier 1 metrics to watch weekly.*

**1 — A5 (Wrong-Bucket Rate)**
Dimension: Scoring Quality.
This is the primary quality signal. The directional split between false alarms and missed opportunities matters — they point to different problems and require different fixes.

**2 — B1 (Confidence Calibration Error)**
Dimension: Accuracy Proxy.
Calibration is the central promise of the product. If the confidence numbers are dishonest, every downstream decision built on them is unreliable.

**3 — B2 (Confidence Distribution Shape)**
Dimension: Accuracy Proxy.
This is an early warning system for upstream data quality. If the distribution collapses toward low-confidence, something in Agent C's input pipeline has changed.

**4 — C1 (Cross-Run Variance)**
Dimension: Consistency.
This is the trust signal. A single bucket flip on re-submission destroys salesperson confidence in the system more than almost any other failure mode.

**5 — C3 (Distribution Drift Detection)**
Dimension: Consistency.
This catches silent regressions — LLM provider updates, persona drift, data source changes — that have no obvious trigger. It is the canary in the coal mine.

**6 — D2 (Action Distribution Ratio)**
Dimension: Action Relevance.
This is the hardest available signal that users are actually acting on the buckets. If HOT call rate is not at least 3 times COLD call rate, the scoring is being politely ignored.

**7 — D3 (Feedback Rate and Quality)**
Dimension: Action Relevance and Meta.
Everything else depends on feedback volume. If feedback falls below 20%, the system has lost the human signal that makes calibration, audit, and improvement possible.

### Tier 0 North Stars

**A2 — HOT:COLD Conversion Ratio**
Target: at least 2.5 times.
This is the proof that the scoring has real signal — that HOT actually means something in the real world.

**D5 — Per-Salesperson Conversion Lift**
Target: median lift of at least +20%.
This is the proof that the scoring actually changes behaviour and produces measurable business outcomes. Without this, the product has not done its job.

Everything else in this framework is diagnostic in service of these two.

---

## 9. Caveats & Gaps

- **Counterfactual measurement is structurally limited.** The Curiosity Budget is the best available mitigation but does not fully solve it. True recall — what did we miss in COLD? — will always be estimated, not directly observed.
- **No empirical grounding yet.** All targets are defensible starting points, not validated thresholds. They should be revisited and adjusted after the first quarter of production data.
- **Adaptive layer metrics not covered.** Add-on 7 introduces per-signal integrity, lift, stability, and independence metrics. Those are deferred alongside the feature itself.
- **Tenant asymmetry.** Urvee (high volume, short cycle) and Gamoft (low volume, long cycle) will produce very different sample sizes. Some metrics — particularly B1 ECE — may never reach statistical significance for Gamoft alone.

---

## 10. Follow-up Questions

- Which of the 8 decisions in Section 7 should be resolved first? The recommendation is Decision 2 (Curiosity Budget) and Decision 3 (baseline capture) — both must be in place before launch or they become structurally unrecoverable.
- Does Gamoft's long B2B cycle make it unsuitable for the same KPI framework as Urvee? It may need a separate milestone-based scorecard.
- Should this framework itself be versioned and reviewed quarterly as the system matures?
- How does this framework interact with tenant-facing reporting? Tenants likely want simpler numbers than this internal diagnostic view.

---

## Sources Consulted

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 10.3 (confidence routing), 10.4 (explainability), 11.2 (SLA), 11.3 (decay), 11.5 (observability), 11.6 (feedback v1), 17 (deferred adaptive), 19.9 (confidence reasoning)

## Related Concepts

- [[concepts/confidence-first-class]] — Confidence Calibration Error (B1) validates the confidence calculation choice
- [[concepts/feedback-loop]] — D3 and M2 depend on the v1 feedback mechanism
- [[concepts/lineage-log]] — M1 is a hard dependency of every other metric
- [[concepts/score-decay]] — C5 validates decay determinism
- [[concepts/action-sla]] — D1 measures SLA compliance; D2 measures SLA behavioural impact
- [[concepts/disqualification-gate]] — disqualification rate stability is a diagnostic metric
- [[concepts/persona-layer]] — A4 Cross-Tenant Divergence validates persona isolation works
- [[concepts/lead-pipeline-architecture]] — all metrics fit within the 7-phase flow
- [[concepts/adaptive-signal-lifecycle]] — deferred; introduces signal-level metrics when built
