# Wiki Log

*Append-only. Most recent entries at top.*

---

## [2026-04-17] analysis | Scoring Quality Metrics — Global KPIs Section Added

- File updated: wiki/analyses/scoring-quality-metrics.md
- Added Global KPIs section at end of document
- 3 global KPIs: System Health (Pipeline Coverage + Score Stability), Business Health (Scoring Lift + HOT Response Rate), Tenant Health Rate (composite, blocked until Month 1 baseline)
- Written for non-technical readers — plain language, no jargon
- Pairs kept separate within each KPI to prevent hidden failures from averaging

---

## [2026-04-17] schema-update | Scoring Quality Metrics — Universal Formula Rewrite

- File updated: wiki/analyses/scoring-quality-metrics.md
- All formulas rewritten using plain descriptive names — no Greek symbols, no subscript notation, no set operators
- Formulas now self-explanatory at first glance for any audience
- Variable sections retained for data source context
- Metrics without a single formula retain their explanation of why plus a plain-language calculation method

---

## [2026-04-17] schema-update | Scoring Quality Metrics — Mathematical Formula Pass

- File updated: wiki/analyses/scoring-quality-metrics.md
- All formulas rewritten in mathematical notation with named variables
- Every variable explained with its data source
- Metrics without a single formula: AP2 Part 1 (relational check), AP3 (completeness formula pending count vs weight decision), C3 (blocked on TBD thresholds — skeleton formula provided), C5 (deterministic engineering check — no statistical formula appropriate), AR3 (distribution — formula given per-lead, then three aggregates), AR4 (breakdown — per-type formula given, no pass/fail formula), AR5 (session definition pending team decision)
- One open decision surfaced: AP3 completeness formula needs count-based vs weight-based decision from team

---

## [2026-04-17] schema-update | Accuracy Proxy — AP2 + AP3 Combined

- Files updated: wiki/analyses/scoring-quality-metrics.md, wiki/analyses/accuracy-proxy-metrics.md
- Change: AP2 (Monotonicity Check, diagnostic) and AP3 (Discrimination Ratio, primary) merged into single primary metric AP2 (Bucket Separation)
- AP3 slot reassigned to Completeness Qualifier (previously AP4)
- Reason: both metrics used same BOR values and were always read together; separating them was artificial

---

## [2026-04-17] analysis | Scoring Quality Metrics — Combined Document

- Wiki page: [[wiki/analyses/scoring-quality-metrics]]
- Contains: Score Coverage Rate (new) + Accuracy Proxy + Consistency + Action Relevance
- Each section is self-contained; nothing moved between groups
- Score Coverage Rate added as prerequisite health check before the three sub-stories
- Individual group files (accuracy-proxy-metrics.md, consistency-metrics.md, action-relevance-metrics.md) retained separately

---

## [2026-04-17] analysis | Action Relevance — Metric Group Card

- Wiki page: [[wiki/analyses/action-relevance-metrics]]
- Part of story: Define scoring quality metrics → sub-story: action relevance
- Primary metrics: AR1 SLA Compliance Rate, AR2 Action Rate by Bucket
- Diagnostic checks: AR3 Time-to-Action Distribution, AR4 Action Type Distribution by Bucket, AR5 Salesperson Priority Alignment
- Open decision: WARM SLA cutoff needs to be locked (48h or 72h) before AR1 can be calculated
- Targets: TBD — product owner and team leads to set after Month 1 data
- Notes: All three scoring quality sub-stories now complete

---

## [2026-04-17] analysis | Consistency — Metric Group Card

- Wiki page: [[wiki/analyses/consistency-metrics]]
- Part of story: Define scoring quality metrics → sub-story: consistency
- Primary metrics: C1 Cross-Run Bucket Stability, C2 Temporal Score Drift
- Diagnostic checks: C3 Boundary Flip Rate (blocked on TBD thresholds), C4 Decay-Rescore Coherence, C5 Signal Contribution Consistency (engineering check)
- Targets: TBD after Month 1 baseline
- Notes: C3 shares the same bucket threshold blocker as confidence-scoring-brainstorm; C5 should be a unit test at build time

---

## [2026-04-17] analysis | Accuracy Proxy — Metric Group Card

- Wiki page: [[wiki/analyses/accuracy-proxy-metrics]]
- Part of story: Define scoring quality metrics → sub-story: accuracy proxy
- Structure: metric group card (no individual KPI cards); primary metrics + diagnostic checks
- Primary metrics: AP1 Bucket Outcome Rate (per bucket), AP3 Discrimination Ratio (BOR_HOT / BOR_COLD)
- Diagnostic checks: AP2 Monotonicity (pass/fail), AP4 Completeness Qualifier (pass/fail)
- Positive outcome definition: any one of — responded, meeting booked, qualified, deal closed, thumbs up; treated equally
- Targets: TBD after Month 1 baseline
- Notes: success-metrics-framework.md and success-metrics-brief.md found deleted from filesystem; noted in index

---

## [2026-04-17] analysis | Success Metrics Brief — Stakeholder Version Created

- Wiki page: [[wiki/analyses/success-metrics-brief]]
- Trigger: User request — full framework is too long to present to a boss; condensed version needed
- Action: New file created; existing framework untouched
- Same 12 metrics, same 4 dimensions, same 2 hard targets
- Each metric reduced to 2-4 sentences: why it exists, what the calculation does, where any number comes from
- Links back to [[analyses/success-metrics-framework]] for full detail

---

## [2026-04-17] analysis | Success Metrics Framework — v3 Full Explanatory Rewrite

- Wiki page: [[wiki/analyses/success-metrics-framework]]
- Trigger: User review — previous versions listed metrics without explaining why each exists or how calculations work
- Action: Full rewrite in plain English; every metric explains its WHY, every calculation explains its basis, every threshold explains where it comes from and why that number
- Structure retained: 4 dimensions (Scoring Quality, Accuracy Proxy, Consistency, Action Relevance), 12 metrics, 2 hard targets (CO1 ≥90%, CO2 ≤5pt)
- Key explanations added: ground truth problem (why accuracy is measured via proxies), why bucket boundaries are guesses not data-derived, why 5pt is the CO2 limit, why feedback is tracked per bucket not overall, why decay-rescore coherence matters, why SLA windows are tenant-capacity-dependent
- Blockers still documented: bucket score boundaries (most urgent), human review SLA window, CRM data source, feedback loop go-live

---

## [2026-04-17] analysis | Confidence Scoring Brainstorm

- Wiki page: [[wiki/analyses/confidence-scoring-brainstorm]]
- Status: IN PROGRESS — user not yet clear, discussion to resume
- What was established:
  - Signals + weights are per-tenant, per-persona (dev team configures)
  - Three types of uncertainty exist: data, signal contradiction, boundary proximity
  - Enrichment-based confidence (weighted signal coverage) is circular — ruled out
  - Boundary proximity is the only thing confidence can add that enrichment score doesn't
- What changed: confidence-first-class.md marked UNDER REVIEW; previous 2026-04-16 decision on calculation method reopened
- Blocker: bucket thresholds (HOT/WARM/COLD score boundaries) are TBD — confidence formula cannot be finalised without them
- Next step: define bucket boundaries, then resume confidence discussion

---

## [2026-04-16] schema-update | Confidence Calculation + Metrics Framework Revised

**Change 1 — confidence-first-class.md**
- Resolved TBD: confidence is derived from enrichment score threshold, not LLM self-reported
- Reasoning: LLMs are poorly calibrated at self-reporting certainty; deterministic calculation is more reliable
- Routing logic unchanged; only the calculation method is now decided

**Change 2 — success-metrics-framework.md**
- Replaced over-engineered v1 (25+ metrics, assumption-based targets, statistical formulas) with lean v2
- 12 metrics across 4 dimensions, split by when data is actually available
- No targets set upfront except 2 hard operational ones (CO1 prompt coverage, CO2 cross-run stability)
- Removed: ECE, KL divergence, shadow re-runs, 4-tier hierarchy, 25-scenario edge case catalogue
- Added: guiding principle — measure first, set targets after Month 1 baseline
- Index: updated

---

## [2026-04-14] analysis | Success Metrics Framework
- Wiki page: [[wiki/analyses/success-metrics-framework]]
- Question: Define measurable product KPIs — scoring quality, accuracy proxy, consistency, action relevance
- Structure: 4-tier hierarchy (North Star → Health Scorecard → Diagnostic → Infrastructure), 4 dimensions + Meta, 25 catalogued edge cases, 8 open decisions
- Tier 0 candidates: A2 (HOT:COLD Conversion Ratio ≥2.5×), D5 (Per-Salesperson Lift ≥+20% median)
- Top decision recommendation: adopt Curiosity Budget (5% COLD leads called weekly) and capture pre-launch baseline — both structurally unrecoverable if skipped
- Index: updated (1 analysis added)

---

## [2026-04-14] ingest | Multi-Tenant Adaptive Lead Intelligence Engine — Master Reference
- File: raw/assets/lead_intelligence_engine_reference.md
- Wiki page: [[wiki/sources/2026-lead-intelligence-engine-reference]]
- Entities created: gamoft, urvee-organics, govmen, anishekh (4 new)
- Concepts created: lead-pipeline-architecture, agent-vs-tool-classification, persona-layer, confidence-first-class, lineage-log, disqualification-gate, score-decay, action-sla, capability-registry, feedback-loop, adaptive-signal-lifecycle (11 new)
- Overview: updated with domain, thesis, themes, open questions
- Index: updated (1 source, 4 entities, 11 concepts)
- Notes: First source. Domain is Lead Intelligence Engine POC for Gamoft. ~50 TBDs open across technology stack, tenant personas, DB schemas, and algorithm decisions. Adaptive Signal Lifecycle (Add-ons 6/7/8) explicitly deferred to Sprint 2-3.

---

## [2026-04-14] session-start | Initial Setup
- Schema: CLAUDE.md created
- Structure: wiki/, wiki/sources/, wiki/entities/, wiki/concepts/, wiki/analyses/, raw/, raw/assets/ created
- Index: index.md initialized (0 sources)
- Notes: Fresh vault. Awaiting domain selection and first source ingest.
