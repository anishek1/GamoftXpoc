---
type: analysis
question: "How are prompt templates evaluated for quality and correctness before activation and during production operation?"
date: 2026-05-18
tags: [prompt, evaluation, testing, golden-set, regression, quality, offline-evaluation, online-monitoring]
sources_consulted:
  - "[[analyses/prompt-template-framework]]"
  - "[[analyses/prompt-orchestration-framework]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/scoring-quality-metrics]]"
  - "[[analyses/llm-operational-safeguards]]"
  - "[[concepts/signal-types]]"
status: COMPLETE
---

# Prompt Evaluation Framework

**System:** Multi-Tenant Adaptive Lead Intelligence Engine  
**Version:** 1.0.0  
**Date:** 2026-05-18

**Scope:** Pre-deployment (offline) evaluation of new prompt versions, the golden test set, evaluation dimensions, passing criteria, regression detection, and how online production metrics close the loop.

**Relationship to production monitoring:** This framework covers evaluation before a prompt goes live. Once live, the scoring quality metrics (AP1–AP5, C1–C5, AR1–AR5 in [[analyses/scoring-quality-metrics]]) monitor ongoing performance. Both layers are required — offline evaluation catches problems before they reach salespeople; online monitoring catches drift.

---

## 1. When Evaluation Runs

Prompt evaluation is mandatory before any `draft` → `active` state transition in `prompt_registry`.

| Trigger | Evaluation required? | Who reviews |
|---|---|---|
| New tenant's first prompt (pipeline 2 complete) | Yes — automated checks only | System auto-approves if all checks pass |
| Persona Agent re-run (existing tenant) | Yes — automated + team lead review | Team lead approves after automated pass |
| Patch version (wording correction) | Yes — automated checks only | System auto-approves if all checks pass |
| MAJOR system version bump | Yes — full evaluation against all tenants' test sets | Engineering + team lead per tenant |

**No prompt version activates without completing all mandatory evaluation checks for its trigger type.**

---

## 2. Evaluation Dimensions

Every prompt evaluation covers six dimensions. Dimensions 1–4 are automated; dimensions 5–6 require human judgment.

| # | Dimension | What it checks | Method |
|---|---|---|---|
| 1 | **Schema compliance** | All outputs match OUTPUT_SCHEMA exactly; no malformed JSON | Automated |
| 2 | **Score monotonicity** | Higher-intent leads score higher than lower-intent leads on the same tenant | Automated (pair tests) |
| 3 | **Instruction following** | LLM respects all prompt rules (no hallucinated signal values, `not_detected` handled correctly, no markdown in output) | Automated (output scan) |
| 4 | **Sub-score consistency** | `sub_scores.fit + intent + engagement + behaviour + context = score` (tolerance ±1) | Automated |
| 5 | **Reasoning quality** | Reasoning references actual signals; no fabricated signal references; recommended_action is appropriate for the score | Team lead review (sample of 5–10 cases) |
| 6 | **Edge case handling** | All edge cases in test set produce sensible output | Team lead review |

---

## 3. Golden Test Set

Each tenant has a **golden test set** of 20–30 test cases created at onboarding. The test set is stored in the `prompt_evaluation` table and remains stable across prompt versions (the same cases are used to compare versions).

### 3.1 Required Case Categories

Every tenant's golden test set must contain at least one case from each of the following categories:

| Category | Description | Purpose |
|---|---|---|
| **STRONG_FIT_HIGH_INTENT** | All fit signals true + 4+ intent signals true, completeness ≥ 0.85 | Should score 75–100 (HOT or high WARM) |
| **GOOD_FIT_LOW_INTENT** | Fit signals match ICP, but no explicit intent signals | Tests that fit alone does not produce HOT |
| **HIGH_INTENT_POOR_FIT** | Strong intent signals but company/profile does not match ICP | Tests ICP disqualification doesn't fully block a high-intent lead |
| **DISQUALIFYING_PROFILE** | Matches a disqualifying profile in the ICP (e.g., student, reseller) | Should score 0–20 (COLD) |
| **LOW_COMPLETENESS** | Most signals `not_detected`, completeness < 0.50 | Should trigger `needs_review` routing; score should reflect uncertainty |
| **RETURNING_LEAD** | A lead that was previously COLD now shows high-intent signals | Tests `returning` variant correctly upgrades score |
| **RESCORE_WITH_FEEDBACK** | A WARM lead with salesperson feedback: "confirmed budget" | Tests `rescore` variant moves score toward HOT |
| **ALL_NOT_DETECTED** | Every signal is `not_detected`, completeness near 0 | Score should be near 0; reasoning should name the absence |
| **CONFLICTING_SIGNALS** | Strong fit but strong disqualification signals present | Tests LLM's reasoning under conflict |
| **BOUNDARY_SCORE** | Lead designed to score near HOT/WARM boundary (score ~78–82) | Tests threshold enforcement and bucket consistency |

### 3.2 Test Case Format

Each test case is a complete INPUT_SCHEMA-valid payload with three additions:

```json
{
  "test_case_id": "uuid",
  "description": "STRONG_FIT_HIGH_INTENT — Rohan Mehta, CTO, Series A SaaS, all intent signals",
  "expected_bucket": "hot",
  "expected_score_range": { "min": 75, "max": 100 },
  "expected_needs_review": false,
  "must_appear_in_reasoning": ["pricing_request", "demo_requested"],
  "must_not_appear_in_reasoning": [],
  ... (full INPUT_SCHEMA payload)
}
```

`expected_score_range` is a range, not a fixed value — LLM scoring is non-deterministic and a ±5 point variance is acceptable. `expected_bucket` is the primary pass/fail criterion.

### 3.3 B2B vs B2C Test Sets

Test sets are per-tenant. The case categories above apply to both modes. B2B test sets use company-level signal values; B2C test sets use individual/purchase-level signal values.

**For the 3 POC tenants:**
- **Gamoft (B2B):** 20 cases. Authored by the product team before Pipeline 2 runs. Source: real representative leads (anonymised) + synthetic edge cases.
- **Urvee Organics (B2C):** 20 cases. Authored using purchase history patterns from B2C data acquisition.
- **Govmen:** 15 cases. Authored when business_type and persona are confirmed.

---

## 4. Evaluation Procedure

### Step 1 — Run Automated Checks

For each test case in the tenant's golden test set, run the prompt version under evaluation with the test case input. Record:
- Raw LLM output
- Schema validation result (pass/fail)
- Bucket result (`hot`/`warm`/`cold`)
- Score
- sub_scores sum check
- Whether `expected_bucket` matches actual bucket
- Whether `expected_score_range` is met
- Whether `must_appear_in_reasoning` signals appear in `reasoning.signal_contributors`

**Automated check thresholds:**
- Schema compliance: 100% pass required (zero tolerance)
- Bucket accuracy: ≥ 90% of test cases must land in `expected_bucket`
- Score range: ≥ 85% of test cases must land within `expected_score_range`
- sub_scores sum: 100% pass required

If any threshold is not met, the prompt version remains in `draft` status. The failure report is sent to the team lead.

### Step 2 — Team Lead Review (for re-run versions)

The team lead reviews a randomly selected sample of 5–10 outputs, including at least one case from each category. The team lead checks:
- Does `reasoning.salesperson_note` make sense for the lead?
- Does `recommended_action` match the score (e.g., `call_immediately` for HOT, not `nurture`)?
- Are there any factual errors (the LLM cites a signal that was `not_detected` in the input)?

The team lead records a pass/fail judgment per reviewed case and a brief note on any failures.

**Passing criterion for team lead review:** No more than 1 failure out of the reviewed sample. If 2+ cases fail, the prompt is sent back for revision.

### Step 3 — Activate or Reject

If automated checks pass AND team lead review passes (where required), the prompt version transitions from `draft` → `active` in `prompt_registry`. The previous active version transitions to `deprecated`.

If either check fails, the prompt stays in `draft`. The failure log is attached to the `prompt_registry` row.

---

## 5. Regression Detection

When a new prompt version replaces an existing active version, the new version must not regress against the current version.

**Regression test:** Run both the `old_active` and the `new_draft` versions against the same golden test set. Compare:

| Metric | Regression threshold |
|---|---|
| Bucket accuracy (% of cases landing in `expected_bucket`) | New version must not be more than 5pp lower than old version |
| Score distribution (mean ± standard deviation across all test cases) | Mean shift ≤ ±5 points; standard deviation must not increase by more than 10 points |
| Schema compliance | New version must match old version (100%) |
| Reasoning reference accuracy | New version must cite at least as many valid signals as old version in `signal_contributors` |

If any regression threshold is breached, the new version is blocked and a regression report is generated. The team lead decides whether to: (a) revise the prompt, (b) re-run the Persona Agent, or (c) accept the regression with documented justification.

---

## 6. Instruction-Following Checks

Beyond schema compliance, the following instruction-following checks scan LLM output for rule violations:

| Check | Rule being verified | How detected |
|---|---|---|
| No hallucinated signals | `reasoning.signal_contributors` must only name signals that exist in `signal_values` | Cross-reference output signals against input signal_values keys |
| `not_detected` handling | A signal listed as `not_detected` must not appear in `reasoning` as a positive contributor | Check direction=positive for any signal that was `not_detected` in input |
| No markdown in output | Raw LLM response must not contain `` ``` `` or `**` | String scan on raw response before JSON parsing |
| `needs_review` constraint | LLM must return `needs_review: false` (always) | Output schema validation |
| `lead_completeness` echo | Output value must match input value (tolerance 0.001) | Cross-field check |

All five checks are automated and run as part of the automated evaluation in Step 1.

---

## 7. Online Monitoring Signals That Indicate Prompt Problems

After a prompt version is activated, the following production metrics serve as early warning indicators of prompt quality issues. When these signals appear, a new evaluation cycle should be initiated.

| Production metric | Threshold that warrants evaluation | Likely cause |
|---|---|---|
| AP2 (Monotonicity) drops below 0.75 | Score rankings are inconsistent with signal strength | Prompt reasoning rules degraded |
| C1 (Bucket Stability) drops below 0.85 | Same lead getting different buckets on re-run | LLM non-determinism exceeded by prompt ambiguity |
| C5 (Signal Contribution Consistency) drops below 0.80 | Signal attribution is inconsistent across leads | Signal definitions in CONTEXT section are ambiguous |
| Schema validation error rate > 2% in production | LLM frequently returning malformed output | Output format section in prompt is ambiguous |
| Team lead feedback rate > 15% (leads flagged as wrongly scored) | Systematic scoring errors | ICP or signal definitions need updating |

These thresholds trigger a Persona Agent re-run recommendation via the feedback loop (see [[analyses/governance-observability-layer]]). After re-run, the new prompt version goes through the full evaluation procedure above.

---

## Open Decisions

| Decision | Status |
|---|---|
| Golden test set authoring tool (manual JSON vs a guided UI) | TBD — manual JSON for POC phase; guided UI post-MVP |
| Automated regression test cadence (run on every re-run or scheduled?) | Runs on every re-run. No scheduled standalone runs at MVP. |
| Whether to persist evaluation results in the database for audit | TBD — recommend yes; evaluation results should be stored against `prompt_registry` row |
| Instruction-following check: whether to use an LLM-as-judge for reasoning quality | Deferred — adds cost and latency; manual team lead review is sufficient for POC phase |
