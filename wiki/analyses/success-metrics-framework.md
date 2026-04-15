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

| # | Trap | Problem | Mitigation |
|---|------|---------|------------|
| 1 | **Counterfactual** | Can only observe outcomes of *called* leads. Cannot measure missed conversions in COLD bucket. True recall is unmeasurable by default. | **Curiosity Budget** — mandate calling 5% of COLD leads per week. Their conversion rate becomes COLD baseline. |
| 2 | **Attribution** | HOT converts → credit goes to score, salesperson, product, or luck. All four get it simultaneously. | **Per-salesperson lift** (intra-user pre/post) isolates system impact from salesperson skill. |
| 3 | **One-number accuracy** | "Accuracy" conflates bucket, explanation, confidence, action — all independent failure modes. | **Decompose into 4 dimensions** with separate metrics per failure mode. |

### 1.3 Terminology Quick Reference

| Term | Definition |
|------|-----------|
| **Tier** | Hierarchy layer (0–3) determining who reviews the metric, how often, what action is taken. |
| **Target** | Threshold defining "good enough." Four types: hard, soft, alert threshold, ratio. |
| **Availability** | Earliest date a metric can be measured meaningfully (Day 0, Week N, Month N). |
| **Curiosity Budget** | Mandated 5% sampling of COLD bucket for baseline conversion measurement. |
| **Shadow re-run** | Independent re-execution of Agent E using a different LLM provider for cross-validation. |

---

## 2. Tier Hierarchy

| Tier | Name | Reviewers | Cadence | # Metrics | Purpose |
|------|------|-----------|---------|-----------|---------|
| **0** | North Star | Leadership, tenant admin | Quarterly | 1–3 total | Defines whether the product is succeeding at its real job. |
| **1** | Health Scorecard | Owner, team lead | Weekly | ≤7 per tenant | Leading indicators for Tier 0. Main operational dashboard. |
| **2** | Diagnostic | Engineer, analyst | On-demand | Unbounded | Drill-down when Tier 1 moves unexpectedly. Answers "why." |
| **3** | Infrastructure | Engineering | Daily / alert | Unbounded | Cost, latency, log integrity, data isolation. |

---

## 3. Target Types (glossary)

| Type | Usage | Example |
|------|-------|---------|
| **Hard** | Pass/fail. Below = bug. | "100% of leads logged with `prompt_version`" |
| **Soft** | Directional. Ramps with maturity. | ">70% SLA compliance Month 1; >85% Month 3" |
| **Alert threshold** | Floor below which system is broken. | "<20% feedback rate triggers alert" (locked) |
| **Ratio** | Relative comparison; less noise-sensitive. | "HOT:COLD conversion ≥ 2.5×" |

**Every target is conditional on:** minimum sample size (N≥30 default), per-tenant baseline (never global-only), and system maturity stage.

---

## 4. Full Metrics Catalog

### 4.1 Dimension A — Scoring Quality

*Answers: is Agent E producing meaningful, differentiated scores?*

| ID | Metric | Tier | Definition | Target | Availability | How It Lies To You |
|----|--------|------|------------|--------|--------------|-------------------|
| **A1** | Bucket–Outcome Alignment Rate | 1 | % of called leads whose confirmed outcome matches bucket (HOT converts/progresses; WARM engages; COLD goes nowhere). | Soft: >75% after calibration. | Month 2+ | Only reflects *called* leads. COLD unmeasured without Curiosity Budget. |
| **A2** | HOT:COLD Conversion Ratio | **0** | conv_rate(HOT called) ÷ conv_rate(COLD called via Curiosity Budget). | Ratio: ≥ 2.5×. | Month 3+ | Small Curiosity Budget sample → wide CI. Requires ≥30 called COLDs per tenant per quarter. |
| **A3** | Dimensional Differentiation Index | 2 | Mean σ across the 5 Agent E sub-scores (Fit / Intent / Engagement / Behavioral / Context). | Soft: σ ≥ 1.5 on 10-pt scale. | Day 0 | LLM may produce templated artificial variance. Cross-check with A4. |
| **A4** | Cross-Tenant Divergence | 2 | Synthetic test leads run through all 3 tenants. % producing different bucket in ≥2 tenants. | Soft: ≥ 60%. | Day 0 (needs test harness) | Test corpus too generic/extreme → artificial result. Must probe persona differences carefully. |
| **A5** | Wrong-Bucket Rate (directional) | 1 | Split into: **false alarm** (HOT that should be cold) and **missed opportunity** (COLD that should be hot). | Soft: false alarm <15%; missed <10%. | Week 4+ | Missed opportunities are silent — only Curiosity Budget catches them. |

### 4.2 Dimension B — Accuracy Proxy (pre-conversion leading indicators)

*Answers: before conversion data arrives, can we detect quality issues?*

| ID | Metric | Tier | Definition | Target | Availability | How It Lies To You |
|----|--------|------|------------|--------|--------------|-------------------|
| **B1** | Confidence Calibration Error (ECE) | 1 | Weighted avg of \|predicted_confidence − actual_outcome_rate\| across confidence bins. Plot as reliability diagram. | Soft: ECE < 0.10; line within ±10% of diagonal. | Month 2+ | Small samples in high-confidence bins → noisy. Needs ≥100 resolved leads per tenant before trusting the diagram. |
| **B2** | Confidence Distribution Shape | 1 | % of leads in each band (≥80%, 50–79%, <50%) per tenant. | Soft: <30% in <50% band; >50% in ≥80% band after calibration. | Day 0 | LLM self-report clusters at round numbers (80%). Look at shape, not averages. |
| **B3** | Completeness Tier Mix | 2 | % leads reaching Agent E as Complete / Partial / Sparse (Agent C classification). | Soft: >60% Complete; <20% Sparse. | Day 0 | "Complete" = field presence, not truthfulness. Populated lead with wrong phone still looks Complete. |
| **B4** | Explanation–Outcome Decoupling | 2 | For converted leads: does salesperson's stated reason match any of Agent E's 3 key reasons? | Soft: ≥ 50% match. | Month 2+ | Post-hoc rationalization. Capture salesperson reason *before* they see Agent E's reasons. |
| **B5** | Shadow Re-run Disagreement Rate | 2 | Re-run 2–5% of leads through a second LLM (different provider). % bucket disagreement. | Soft: <20%; alert sustained >30%. | Day 0 (needs infra) / Month 2 otherwise | Two models can agree for wrong reasons. Triangulate with human reviewer audit. |

### 4.3 Dimension C — Consistency

*Answers: is the system stable and predictable enough to trust?*

| ID | Metric | Tier | Definition | Target | Availability | How It Lies To You |
|----|--------|------|------------|--------|--------------|-------------------|
| **C1** | Cross-Run Variance | 1 | Same lead submitted twice, same prompt version. Measure score delta. | Hard: bucket never flips. Soft: ≤5 pt variance 95% of time. | Day 0 | Provider non-determinism at T=0 (batching quirks) measures provider, not system. |
| **C2** | Prompt Version Logged | 3 | % of leads with non-null `prompt_version` in lineage log. | Hard: 100%. | Day 0 | Autopopulation can fake this. Audit occasionally against prompt hash. |
| **C3** | Distribution Drift Detection | 1 | Week-over-week KL divergence of bucket distribution per tenant. | Alert threshold: KL > 0.15 with no prompt/persona/source change. | Week 2+ | Seasonality looks like drift in early months. Use noise-aware thresholds. Catches silent LLM model updates from provider. |
| **C4** | Baseline Anchor Test | 3 | 10 canonical test leads run daily through production. Compare to historical distribution. | Hard: 10/10 within tolerance. | Day 0 | Anchor corpus must be maintained; stale corpus = stale signal. |
| **C5** | Decay Determinism | 3 | Score changes for inactive leads must match locked decay formula exactly. | Hard: 100% match. | Day 30+ | If decay and feedback adjustments run on the same field, deviations may come from feedback, not decay bug. Log field separately. |

### 4.4 Dimension D — Action Relevance

*Answers: is the scoring actually changing behavior?*

| ID | Metric | Tier | Definition | Target | Availability | How It Lies To You |
|----|--------|------|------------|--------|--------------|-------------------|
| **D1** | HOT SLA Compliance Rate | 1 | % of HOT leads contacted within 24h. | Soft: >70% M1; >85% M3+. | Day 0 | "Contacted" may be auto-logged without genuine contact. Audit contact content sample. |
| **D2** | Action Distribution Ratio | 1 | HOT call rate ÷ COLD call rate. | Ratio: ≥ 3:1. | Day 0+ | Hardest signal that scoring changes behavior vs. being politely ignored. |
| **D3** | Feedback Rate & Quality | 1 | (a) % leads with any feedback tag; (b) % verdicts with reason tag. | (a) Alert: <20%. Soft: >40%. (b) Soft: >60%. | Week 1+ | Thumbs-spam (habit clicking). Catch via reviewer audit + low reason-tag rate. |
| **D4** | Suggested Action Acceptance | 2 | % of leads where salesperson took Agent E's suggested action (call/WhatsApp/email/nurture). | Soft: >50% (below 20% = drop the feature). | Month 1+ | High acceptance may just mean salesperson does default action regardless of suggestion. |
| **D5** | Per-Salesperson Conversion Lift | **0** | Conversion rate per salesperson pre-launch vs post-launch. | Soft: median +20%; bottom quartile non-negative. | Month 3+ | Confounded by market changes, team growth. Mitigate via rolling cohort analysis. |

### 4.5 Dimension M — Meta (metrics about the measurement system itself)

*If these break, everything above is unreliable.*

| ID | Metric | Tier | Definition | Target | Availability |
|----|--------|------|------------|--------|--------------|
| **M1** | Lineage Log Completeness | 3 | % of leads with complete per-step lineage entries. | Hard: 100% (non-negotiable per locked rule). | Day 0 |
| **M2** | Feedback Honesty Audit | 3 | Quarterly human check: does feedback tag match CRM outcome? | Soft: ≥ 85% alignment. | Month 2+ |
| **M3** | Reviewer Agreement Ceiling | 2 | Human reviewer agreement rate with Agent E. | Alert: >95% = rubber-stamping. | Month 1+ |
| **M4** | Sample-Size Sufficiency Flag | 3 | Each metric reports its CI; metrics below N<30 are marked "insufficient data." | Hard: no alerts fire below N threshold. | Day 0 |
| **M5** | Tenant Data Isolation Audit | 3 | Cross-tenant signal leakage. | Hard: 0 instances. | Day 0 |
| **M6** | PII Retention Compliance | 3 | % of log entries past retention window that are scrubbed. | Hard: 100%. | Month 1+ |

---

## 5. Edge Case Catalogue

### 5.1 Cold Start

| # | Scenario | Impact | Mitigation Metric / Rule |
|---|----------|--------|-------------------------|
| 1 | New tenant, no history | No baseline for lift metrics (D5) for 90 days | Use absolute targets first (HOT ≥ X% of book); relative targets after baseline stabilizes. |
| 2 | New source channel mid-quarter | Pollutes distribution trend | Tag metrics with `source_activated_at`; exclude first 2 weeks from trend calcs. |
| 3 | Persona just updated | Performance discontinuity | Include `persona_version` in every metric. Break series explicitly — never smooth across a persona change. |

### 5.2 Feedback Reliability

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 4 | Salesperson marks everything "wrong bucket" (venting) | False negative spike | Per-user verdict diversity metric. Audit users where >80% of verdicts are the same tag. |
| 5 | Salesperson marks everything "converted" (perverse incentive) | False accuracy inflation | Cross-check against CRM conversion record. |
| 6 | Two salespeople disagree on same lead | Ambiguous verdict | Policy decision needed (see Section 7, D5). Store both or pick canonical. |
| 7 | One heavy user dominates feedback volume | Skewed tenant metrics | Cap per-user contribution to aggregate metrics. |

### 5.3 Sales Cycle Length

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 8 | Gamoft B2B cycles = 90–180 days | "Did HOT convert?" unanswerable for 6 months | Milestone-based proxy outcomes (meeting → proposal → contract). Each is a mini-conversion. |
| 9 | Urvee B2C cycles = hours | HOT should convert same-day | SLA framework implicitly tenant-dependent. |

### 5.4 LLM Behavior

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 10 | Malformed JSON from Agent E | Lead has no bucket | Explicit `agent_error` status; track rate; hard target <1%. |
| 11 | Agent E hallucinates a signal | Fake explanation → wrong action | Audit 5% of explanations against raw source. Escalate if hallucination rate >5%. |
| 12 | Token limit truncation | Silent context loss | Log input token count; correlate with outcome quality; near-limit leads should show degraded accuracy. |
| 13 | Provider model silently updated | Score behavior changes | Baseline Anchor Test (C4) catches this. |
| 14 | T=0 non-determinism | Same input → different score | Cross-Run Variance (C1) alerts. |

### 5.5 Operational

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 15 | Rate limit exhausted mid-run | Partial results | Separate `incomplete_fetch` bucket in metrics. Never average into clean runs. |
| 16 | API auth token expired | Pipeline halt | Pipeline completion rate metric; alert on halts. |
| 17 | Dedup merged distinct people (shared phone) | Wrong person scored | Feedback flag "this isn't the expected person" → dedup audit. |

### 5.6 Statistical

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 18 | Simpson's paradox | Global looks good, per-tenant bad | Rule: never report global without per-tenant + cross-tenant variance. |
| 19 | Small-sample false alarms | Alert fatigue | Wilson confidence intervals; suppress alerts below N=30. |
| 20 | Multiple-testing fallacy | 30 KPIs → 1.5 false alarms/week | Bonferroni correction or accept higher per-metric thresholds. |

### 5.7 Adversarial

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 21 | Lead source poisoning | Skewed metrics | Anomaly detection on source volume. |
| 22 | Reviewer rubber-stamping | False reviewer agreement | Inject occasional synthetic "wrong Agent E" outputs; reviewer should catch them (M3 above). |
| 23 | Tenant admin gaming persona | Artificial HOT inflation | Rate-limit persona updates; audit all changes. |

### 5.8 Causal

| # | Scenario | Impact | Mitigation |
|---|----------|--------|------------|
| 24 | "Would have converted anyway" | System gets undeserved credit | A/B hold-out or pre/post + propensity matching. Build comparison infra early. |
| 25 | Salesperson skill drift | Confounds D5 | Rolling quarterly baselines, not a single pre-launch baseline. |

---

## 6. Temporal Rollout Plan

*When each metric becomes measurable.*

| Phase | Available Metrics |
|-------|------------------|
| **Day 0 (POC launch)** | A3, A4 (if harness built), B2, B3, C1, C2, C4, C5, D1, D2, M1, M4, M5 |
| **Week 1–4** | A5 (early feedback), B5 (if shadow infra shipped), C3, D3, D4 |
| **Month 2–3** | A1, B1 (ECE), B4, D5 (needs pre-launch baseline), M2, M3, M6 |
| **Month 3+** | **A2** (requires Curiosity Budget — the Tier 0 metric) |
| **Month 6+** (post-adaptive layer) | Signal-level integrity metrics from deferred [[concepts/adaptive-signal-lifecycle]] |

---

## 7. Decisions Required (open questions)

*Blockers before any of this ships. Resolve each in a dedicated ticket.*

| # | Decision | Depends Metrics | Recommendation |
|---|----------|-----------------|----------------|
| 1 | Confidence calculation method (self-report / completeness / hybrid) | B1, B2, and all confidence-routing logic | **Hybrid**: `confidence = min(signal_completeness, llm_self_reported)`. Floor from data quality, ceiling from LLM judgment. |
| 2 | Curiosity Budget adoption (5% of COLD leads called weekly) | A2 (North Star), A5 missed-opportunity | **Strong yes.** Without this the entire accuracy story is structurally blind. Cheapest item on the list — only salesperson time. |
| 3 | Pre-launch baseline capture (per salesperson, per tenant, ≥30 days) | D5 (North Star) | **Yes**, mandatory. If skipped, no reliable lift measurement ever possible. |
| 4 | Reporting discipline: per-tenant always, never global-only | All metrics | **Lock as a rule.** Dashboard template enforces it. |
| 5 | Canonical verdict source on salesperson disagreement | All feedback-based metrics | Options: most-recent-wins / highest-role-wins / store-both. Pick one; document in schema. |
| 6 | Shadow re-run budget (~5% LLM cost increase) | B5 | **Defer** to Month 3 unless silent failure is high-priority. Start without, add if A1/A5 signal quality issues. |
| 7 | Milestone-based proxy outcomes for long B2B cycles | A1, A2 for Gamoft | Define 3–4 milestones for Gamoft (meeting booked → proposal → contract). Urvee likely doesn't need. |
| 8 | Test harness corpus ownership (C4, A4) | C4, A4 | Assign single owner; refresh quarterly. Otherwise anchor tests rot. |

---

## 8. Minimum Viable Scorecard (the 7 Tier 1 metrics watched weekly)

*If everything else is overwhelming, this is the operational dashboard.*

| # | Metric ID | Dimension | Why It Makes The Short List |
|---|-----------|-----------|-----------------------------|
| 1 | A5 | Scoring Quality | Primary quality signal (directional split matters) |
| 2 | B1 | Accuracy Proxy | Calibration is the feature's central promise |
| 3 | B2 | Accuracy Proxy | Early warning for upstream data quality |
| 4 | C1 | Consistency | Trust signal — bucket flips destroy confidence |
| 5 | C3 | Consistency | Catches silent regressions and provider drift |
| 6 | D2 | Action Relevance | Are users actually using the buckets? |
| 7 | D3 | Action Relevance + Meta | Everything else depends on feedback volume |

### Tier 0 North Stars (the 2 metrics that justify the project's existence)

| ID | Target | Meaning |
|----|--------|---------|
| **A2** HOT:COLD Conversion Ratio | ≥ 2.5× | Proves the scoring has real signal |
| **D5** Per-Salesperson Conversion Lift | ≥ +20% median | Proves the scoring actually drives behavior |

Everything else is diagnostic in service of these two.

---

## 9. Caveats & Gaps

- **Counterfactual measurement is structurally limited.** The Curiosity Budget is the best available mitigation but does not fully solve it. True recall (what did we miss in COLD?) will always be estimated, not observed.
- **No empirical grounding yet.** All targets are defensible starting points, not validated thresholds. They should be adjusted after first quarter of production data.
- **Adaptive layer metrics not covered.** Add-on 7 introduces per-signal integrity, lift, stability, independence. Those are deferred alongside the feature.
- **Tenant asymmetry.** Urvee (high volume, short cycle) vs Gamoft (low volume, long cycle) will produce wildly different sample sizes. Some metrics (B1 ECE) may never reach statistical significance for Gamoft alone.

---

## 10. Follow-up Questions

- Which of the 8 decisions in Section 7 should we resolve first? (Recommendation: #2 Curiosity Budget + #3 baseline capture — both must happen *before* launch or they are structurally unrecoverable.)
- Does Gamoft's long B2B cycle make it unsuitable for the same KPI framework as Urvee? (Possibly needs separate milestone-based scorecard.)
- Should this framework itself be versioned and reviewed quarterly?
- How does this framework interact with tenant-facing reporting? (Tenants likely want simpler numbers than this internal view.)

---

## Sources Consulted

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 10.3 (confidence routing), 10.4 (explainability), 11.2 (SLA), 11.3 (decay), 11.5 (observability), 11.6 (feedback v1), 17 (deferred adaptive), 19.9 (confidence reasoning)

## Related Concepts

- [[concepts/confidence-first-class]] — Confidence Calibration Error (B1) validates the confidence calculation choice
- [[concepts/feedback-loop]] — D3 and M2 depend on the v1 feedback mechanism
- [[concepts/lineage-log]] — M1 is a hard dependency of every other metric
- [[concepts/score-decay]] — C5 validates decay determinism
- [[concepts/action-sla]] — D1 measures SLA compliance; D2 measures SLA behavioral impact
- [[concepts/disqualification-gate]] — disqualification rate stability is a diagnostic metric
- [[concepts/persona-layer]] — A4 Cross-Tenant Divergence validates persona isolation works
- [[concepts/lead-pipeline-architecture]] — all metrics fit within the 7-phase flow
- [[concepts/adaptive-signal-lifecycle]] — deferred; introduces signal-level metrics when built
