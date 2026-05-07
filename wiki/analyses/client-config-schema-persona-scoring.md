---
type: analysis
question: "What are the persona and scoring preference fields in the client configuration schema — covering dimension weights, bucket thresholds, output preferences, and custom rules?"
date: 2026-05-07
tags: [client-config, schema, scoring, persona, banding, weights, output-format, signal-weights]
sources_consulted:
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/llm-io-contract]]"
  - "[[concepts/persona-layer]]"
  - "[[concepts/signal-types]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/client-config-schema-business-profile]]"
status: COMPLETE — Subtask 2 of 3 (Business profile fields in client-config-schema-business-profile; Default and override settings in client-config-schema-defaults)
---

# Client Configuration Schema — Persona and Scoring Preference Fields (Subtask 2 of 3)

**Question:** What are the persona and scoring preference fields in the client configuration schema — covering dimension weights, bucket thresholds, output preferences, and custom rules?
**Date:** 2026-05-07

---

## Plain-English Summary

**Why this exists:** Not every business evaluates leads the same way. A company with a long enterprise sales cycle cares more about whether a lead has declared intent (did they ask for a demo?). A consumer brand running flash sales cares more about whether someone has engaged repeatedly and quickly. This document defines the knobs that make the scoring system work correctly for each specific client — rather than using the same weights for everyone.

**Where it fits:** These settings live in the PersonaObject — the AI-generated configuration profile for each client, stored in the `personas` table and cached for 15 minutes. Every time the system scores a lead, it loads this PersonaObject first. Without it, scoring cannot begin.

**How it works:** After a client completes onboarding, the Persona Agent automatically produces three layers of scoring configuration: (1) how much each of the five scoring dimensions counts toward the total score, (2) what thresholds separate HOT / WARM / COLD leads, and (3) what tone and special rules apply. None of this is set by the client directly — the AI infers it from the client's business description. The only exception is signal-level weights (which signals matter most *within* a dimension), which can be adjusted directly without re-running the entire Persona Agent.

---

## Purpose of This Document

This document defines the **scoring configuration section** of the client configuration schema. It specifies every field that controls how leads are evaluated, scored, bucketed, and surfaced to the salesperson.

All fields in this document are produced by the Persona Agent. None are collected directly from the user. The client's only mechanism for influencing these fields is indirect: the business profile inputs (Subtask 1) feed the Persona Agent, which infers these fields. To change them after initial onboarding, a Persona Agent re-run is required — with the exception of signal-level weights (see Group 5, which can be edited directly).

**What this section covers:**
- Dimension scoring weights (`scoring_weights` in PersonaObject)
- Bucket threshold configuration (`banding` in PersonaObject)
- Output tone preference (`tone` in PersonaObject)
- Custom scoring rules (`custom_rules` in PersonaObject)
- Signal-level weights (`weight_within_dim` in `signal` entity)
- Output format constraint (`recommended_action` enum — per-lead output, not a PersonaObject field)

**What this section does NOT cover:**
- Business profile fields (industry, ICP, geography, target market) → [[analyses/client-config-schema-business-profile]] (Subtask 1)
- Priority signals and disqualifying signals → covered in Subtask 1 (Group 3, IcpDefinition fields)
- Per-tenant operational limits (concurrency cap, token budgets, tier assignment) → [[analyses/client-config-schema-defaults]] (Subtask 3)

---

## Answer / Finding

The scoring configuration section has five field groups stored in the data layer, plus one per-lead output format constraint:

1. **Dimension Scoring Weights** — per-tenant LLM-inferred weights for each scoring dimension
2. **Bucket Threshold Configuration** — per-tenant thresholds that determine HOT / WARM / COLD assignments
3. **Output Tone Preference** — per-tenant tone style that shapes LLM-generated salesperson notes
4. **Custom Scoring Rules** — per-tenant rule strings that express constraints outside the five-dimension framework
5. **Signal-Level Weights** — per-signal weights within each dimension (the only group editable without a re-run)
6. **Output Format Constraint** — the `recommended_action` 7-value enum (per-lead LLM output; not a PersonaObject field)

**Critical rule:** No form field, admin panel, or API endpoint should allow direct user input into Groups 1–5. All five groups are owned by the Persona Agent. Changes require a Persona Agent re-run with explicit team lead approval — except signal-level weights (Group 5), which can be edited directly.

Two known inconsistencies in the current spec are flagged under Caveats.

---

## The Three Levels of Scoring Configuration

Before the field groups, this architectural summary prevents a common confusion:

```
Level 1 — Dimension weights (PersonaObject.scoring_weights)
  "How much does each of the five dimensions matter?"
  Granularity: per dimension (5 values)
  Stored in: personas entity
  Change path: full Persona Agent re-run

       │ determines proportional contribution to total score
       ▼

Level 2 — Signal weights (signal.weight_within_dim)
  "Within a dimension, how much does each signal matter?"
  Granularity: per signal (many values, varies by tenant)
  Stored in: signal entity
  Change path: direct edit (no re-run required)

       │ signal values fill prompt slots; LLM evaluates per slot
       ▼

Level 3 — Bucket thresholds (PersonaObject.banding)
  "Given the final 0–100 score, what bucket does this lead land in?"
  Granularity: two threshold values (hot_min, warm_min)
  Stored in: personas entity
  Change path: full Persona Agent re-run
```

---

## Group 1 — Dimension Scoring Weights

Produced by **Persona Agent Step 1**. These five values determine the proportional contribution of each scoring dimension to the final 0–100 lead score.

### Fields

| Field | Type | Default | Min | Max | Storage Entity |
|-------|------|---------|-----|-----|----------------|
| `scoring_weights.fit` | float | 0.25 | 0.0 | 1.0 | `personas` (PersonaObject) |
| `scoring_weights.intent` | float | 0.25 | 0.0 | 1.0 | `personas` (PersonaObject) |
| `scoring_weights.engagement` | float | 0.20 | 0.0 | 1.0 | `personas` (PersonaObject) |
| `scoring_weights.behaviour` | float | 0.20 | 0.0 | 1.0 | `personas` (PersonaObject) |
| `scoring_weights.context` | float | 0.10 | 0.0 | 1.0 | `personas` (PersonaObject) |

**Default weight set:**
```json
{
  "fit":        0.25,
  "intent":     0.25,
  "engagement": 0.20,
  "behaviour":  0.20,
  "context":    0.10
}
```

### Invariant — Weights Must Sum to 1.0

All five values must sum to exactly 1.0 (tolerance ± 0.001). This invariant is enforced at two points:

1. **Persona Agent Step 1 output:** The orchestrator validates the sum immediately after receiving the PersonaObject. If weights don't sum to 1.0, the orchestrator retries once with a correction instruction appended to the prompt. If still failing, Pipeline 2 halts and an admin is alerted. (source: [[analyses/persona-agent-spec]] §Step 1 Constraint)
2. **Every Pipeline 1 pre-flight check:** The Persona Engine validates weights before any `score_lead()` call. `PersonaInvalidError` is a hard failure — the affected lead is routed directly to `human_review` without calling the LLM. (source: [[analyses/rating-agent-spec]] §Component 1, [[analyses/llm-io-contract]] cross-field rule `WEIGHT_SUM`)

**Why the Persona Agent infers these rather than letting clients set them directly:** Different businesses have fundamentally different conversion dynamics. A B2B enterprise software company's leads are rarely warm without explicit intent signals — Intent should dominate. A B2C impulse-purchase brand is more driven by behavioural signals (repeat views, engagement patterns) than declared intent. The LLM infers appropriate weights from the business context rather than requiring clients to understand the five-dimension framework well enough to weight it manually.

### Sub-Score Ceiling Derivation

The maximum achievable sub-score for each dimension is the dimension weight × 100. At default weights:

| Dimension | Weight | Sub-Score Ceiling |
|-----------|--------|-------------------|
| `fit` | 0.25 | 25 pts |
| `intent` | 0.25 | 25 pts |
| `engagement` | 0.20 | 20 pts |
| `behaviour` | 0.20 | 20 pts |
| `context` | 0.10 | 10 pts |
| **Total** | **1.00** | **100 pts** |

**⚠ Known inconsistency — see Caveats §1.** The current LLM I/O contract (`llm-io-contract.md`) hardcodes these ceilings as schema validation ranges (e.g., `sub_scores.fit: max 25`). This is correct at default weights but becomes invalid if weights are overridden. See Caveats for the full impact.

---

## Group 2 — Bucket Threshold Configuration

Produced by **Persona Agent Step 1**. These thresholds determine which bucket a lead lands in after the final score is calculated.

### Fields

| Field | Type | Default | Description | Storage Entity |
|-------|------|---------|-------------|----------------|
| `banding.hot_min` | integer (1–100) | 80 | Score ≥ hot_min → HOT bucket | `personas` (PersonaObject) |
| `banding.warm_min` | integer (1–100) | 55 | Score ≥ warm_min AND < hot_min → WARM bucket | `personas` (PersonaObject) |
| `banding.cold_max` | integer | 54 | Score < warm_min → COLD bucket (always = warm_min − 1) | `personas` (PersonaObject) |

**Default banding:**
```json
{
  "hot_min":  80,
  "warm_min": 55,
  "cold_max": 54
}
```

### Bucket Assignment Logic

```
score ≥ hot_min (80)             → HOT
score ≥ warm_min (55) AND < hot_min (80) → WARM
score < warm_min (55)            → COLD
```

### Field Notes

**`cold_max` is derivable but stored explicitly.** It is always `warm_min − 1`. It is stored as a separate field in the PersonaObject rather than derived at read time to prevent off-by-one ambiguity in query logic. Any code reading `banding.cold_max` must validate that it equals `warm_min − 1`; a mismatch indicates a corrupt PersonaObject.

**Invariant — Threshold Order:** `warm_min < hot_min`. The cross-field rule `THRESHOLD_ORDER` in the LLM I/O contract enforces this at the input validation layer — a PersonaInvalidError halts scoring for the tenant if this is violated. (source: [[analyses/llm-io-contract]] §VALIDATION_RULES cross_field_rules)

### Banding Enforcement

Banding is enforced by the **Output Schema Layer** (Component 4 of the Rating Agent). The LLM independently outputs both a `score` integer and a `bucket` string. If the LLM's bucket claim is inconsistent with its own score and the tenant's banding thresholds, the threshold-derived bucket wins — and the discrepancy is logged to the `lineage_record`. The LLM never overrides banding. (source: [[analyses/rating-agent-spec]] §Component 4, [[analyses/llm-io-contract]] cross-field rule `BUCKET_SCORE_CONSISTENCY`)

**Why banding is inferred rather than fixed:** Tenants with different sales cycles and qualification standards need different HOT thresholds. A high-volume consumer brand might accept WARM at score 45. An enterprise B2B company might only want HOT actions on score 85+. Forcing a global 80/55 split would produce the wrong action distribution for most tenants.

---

## Group 3 — Output Tone Preference

Produced by **Persona Agent Step 1**.

### Field

| Field | Type | Description | Storage Entity |
|-------|------|-------------|----------------|
| `tone` | string | Per-tenant communication style preference for LLM-generated output | `personas` (PersonaObject) |

**Examples from persona-agent-spec:** Not explicitly enumerated — the field is a free-text string produced by the Persona Agent (e.g., `"direct and data-driven"`, `"conversational"`, `"formal B2B"`, `"warm consumer-friendly"`).

### ⚠ Gap — Downstream Consumption Not Documented

`tone` is defined in the PersonaObject schema (source: [[concepts/persona-layer]], [[analyses/persona-agent-spec]]) and is produced by Persona Agent Step 1. However, the LLM I/O contract's `persona` input object does not include `tone` as a field. (source: [[analyses/llm-io-contract]] §INPUT_SCHEMA `persona` properties — only `tenant_name, business_type, icp_summary, disqualifying_profiles, scoring_weights, hot_min, warm_min, persona_version` are listed.)

**What this means in practice:** `tone` is stored in the `personas` table but it is not confirmed to reach the Rating Agent's LLM call. Either:
- The INPUT_SCHEMA in `llm-io-contract` is incomplete and needs `tone` added
- `tone` is injected via the system prompt template rather than as a structured input field (not documented)
- `tone` has no active downstream effect yet (stored, not wired)

This is a gap between the PersonaObject schema and the LLM I/O contract. It must be resolved before the Rating Agent is implemented. Do not invent details about what `tone` currently influences.

---

## Group 4 — Custom Scoring Rules

Produced by **Persona Agent Step 1**.

### Field

| Field | Type | Description | Storage Entity |
|-------|------|-------------|----------------|
| `custom_rules` | `string[]` | Tenant-specific scoring constraints that don't fit the five-dimension framework | `personas` (PersonaObject) |

**What custom rules look like:** Each entry is a natural-language rule string. Examples from the knowledge base include notes like: "insufficient input to infer sales_cycle — team lead supplement required." Inferred from context, other examples might include: "leads without company information should have Fit sub-score capped", "flag leads from competitor domains regardless of intent signals." The Persona Agent derives these from `negative_profiles`, business context, and ICP context.

### ⚠ Gap — Downstream Consumption Not Documented

Same gap as `tone`: `custom_rules` appears in the PersonaObject schema but is not present in the `persona` input object in the LLM I/O contract. (source: [[analyses/llm-io-contract]] §INPUT_SCHEMA)

This is a second field stored in PersonaObject whose wiring into the Rating Agent prompt is undocumented. Either the INPUT_SCHEMA is incomplete, the rules are injected via the prompt template (not documented), or they have no active downstream effect yet. Resolve before implementation.

**When `custom_rules` is written with a `null` note:** Per the Persona Agent failure handling, if a required field cannot be inferred with sufficient confidence, the Persona Agent writes `null` and appends an explanatory entry to `custom_rules` (e.g., `"sales_cycle: could not infer — business_description insufficient; team lead to supplement"`). This is how the Persona Agent surfaces its own uncertainty without fabricating values. (source: [[analyses/persona-agent-spec]] §Failure Handling)

---

## Group 5 — Signal-Level Weights

Produced by **Persona Agent Step 3**. These are the only scoring configuration fields that can be edited directly without a full Persona Agent re-run.

### Field

| Field | Type | Description | Storage Entity |
|-------|------|-------------|----------------|
| `weight_within_dim` | float (0.0–1.0) | This signal's contribution weight within its parent dimension | `signal` entity |

This field lives on each individual `signal` record, not on the PersonaObject.

### Structure

Each signal belongs to exactly one dimension. Within a dimension, all signals' `weight_within_dim` values must sum to 1.0. The Persona Agent Step 3 validates this at output time; the orchestrator validates after receiving the signal set. (source: [[analyses/persona-agent-spec]] §Step 3 Constraint, §Failure Handling)

**Example (Intent dimension):**
```json
{ "signal": "pricing_request",  "dimension": "intent", "weight_within_dim": 0.30 },
{ "signal": "demo_requested",   "dimension": "intent", "weight_within_dim": 0.20 },
{ "signal": "urgency_language", "dimension": "intent", "weight_within_dim": 0.20 },
{ "signal": "timeline_stated",  "dimension": "intent", "weight_within_dim": 0.15 },
{ "signal": "budget_mentioned", "dimension": "intent", "weight_within_dim": 0.15 }
// weights sum: 0.30 + 0.20 + 0.20 + 0.15 + 0.15 = 1.00 ✓
```

### The Edit-Without-Re-Run Asymmetry

Signal-level weights are the **only scoring configuration field** that can be adjusted directly (e.g., by editing the `signal` record) without triggering a full Persona Agent re-run. The persona-agent-spec explicitly states:

> "Minor updates (adjusting a signal weight, editing a prompt) go directly to their respective records — no Persona Agent re-run needed."

(source: [[analyses/persona-agent-spec]] §When it does NOT run)

**Why this asymmetry exists:** Dimension-level weight changes (scoring_weights) alter the fundamental scoring economics — they affect how much each dimension contributes to the total score. Such changes have system-wide implications for a tenant's scoring distribution and require a full re-run to maintain a consistent, coherent PersonaObject. Signal-level weight changes within a dimension are more surgical — they adjust which *signals* matter most within a dimension whose total contribution is unchanged. These are safe to adjust without a full re-run.

**Constraint that still applies after direct edit:** Weights within each dimension must still sum to 1.0 after any direct edit. The orchestrator or an admin tool must validate this before the edited signal set is committed.

---

## Group 6 — Output Format Constraint: `recommended_action` Enum

`recommended_action` is **not a PersonaObject field**. It is produced per-lead by the Rating Agent LLM and returned as part of `ScoringOutput`. It is documented here because it defines the output format that scoring preference configuration shapes.

### The Enum

The LLM I/O contract hardened `recommended_action` from a freeform string to a 7-value enum: (source: [[analyses/llm-io-contract]] §OUTPUT_SCHEMA)

| Value | Intended Context |
|-------|-----------------|
| `call_immediately` | HOT lead; strong fit + intent; time-sensitive |
| `schedule_demo` | HOT or high-WARM; product interest without immediate close readiness |
| `send_pricing_deck` | Strong intent with pricing question; move to next stage |
| `follow_up_scheduled` | WARM; lead is engaged but not urgent; set a specific date |
| `send_qualifying_message` | WARM or uncertain; gather missing qualification data |
| `nurture` | COLD or low-WARM; keep in sequence but no immediate action |
| `archive` | COLD and disqualified, or explicitly excluded by negative_profiles |

### Relationship to Tenant Persona

The tenant's `banding`, `scoring_weights`, and business_type all influence which action the LLM selects per lead — a HOT bucket on a long-cycle B2B persona maps more naturally to `schedule_demo` than `call_immediately`. The `recommended_action` is the LLM's synthesis of the score and the persona context into a specific salesperson instruction.

### Open Design Decision — Per-Tenant Enum Extension

The current 7-value enum is global — all tenants use the same action set. The `llm-io-contract` flags an unresolved question: should this enum be extensible per tenant via the PersonaObject? (source: [[analyses/llm-io-contract]] §Follow-up Questions)

For example, a B2C brand might want a custom action like `send_whatsapp_offer` that doesn't exist in the global enum. Until this is resolved, all tenants share the 7 values. This is documented as an open decision in Caveats.

---

## Change Management Summary

| Field Group | Inferred By | Can Be Changed | Change Path |
|-------------|-------------|---------------|-------------|
| `scoring_weights` (5 fields) | Persona Agent Step 1 | Yes | Full Persona Agent re-run; team lead approval required |
| `banding` (hot_min, warm_min, cold_max) | Persona Agent Step 1 | Yes | Full Persona Agent re-run; team lead approval required |
| `tone` | Persona Agent Step 1 | Yes | Full Persona Agent re-run; team lead approval required |
| `custom_rules` | Persona Agent Step 1 | Yes | Full Persona Agent re-run; team lead approval required |
| `weight_within_dim` (per signal) | Persona Agent Step 3 | Yes | **Direct edit to `signal` record — no re-run required** |
| `recommended_action` enum values | Global schema (llm-io-contract) | No (currently) | Would require schema version update; per-tenant extension TBD |

**What "team lead approval" means:** A Persona Agent re-run never starts without explicit `team_lead_approval = true`. The system proposes the re-run (triggered by governance feedback loop or check-in); the team lead approves or rejects it. This is a locked design decision. (source: [[analyses/persona-agent-spec]] §Invocation Conditions)

**What a re-run changes:** A full Persona Agent re-run regenerates all three steps — PersonaObject (Step 1), IcpDefinition (Step 2), and signal definitions (Step 3). It does not allow re-running only Step 1 to change scoring_weights while preserving Step 3 signal definitions — except in the case of feedback-driven re-runs where only ICP+Signal steps are re-run. (source: [[analyses/persona-agent-spec]] §Open Decisions)

---

## Fields Explicitly NOT User Inputs

All fields in Groups 1–5 are produced by the Persona Agent. None are collected from the user at any stage. The client influences them only through their business profile inputs in Stage 3 onboarding.

| Field | Produced By | Form Input? |
|-------|-------------|-------------|
| `scoring_weights.fit` | Persona Agent Step 1 | No |
| `scoring_weights.intent` | Persona Agent Step 1 | No |
| `scoring_weights.engagement` | Persona Agent Step 1 | No |
| `scoring_weights.behaviour` | Persona Agent Step 1 | No |
| `scoring_weights.context` | Persona Agent Step 1 | No |
| `banding.hot_min` | Persona Agent Step 1 | No |
| `banding.warm_min` | Persona Agent Step 1 | No |
| `banding.cold_max` | Persona Agent Step 1 | No |
| `tone` | Persona Agent Step 1 | No |
| `custom_rules` | Persona Agent Step 1 | No |
| `weight_within_dim` | Persona Agent Step 3 | No |

---

## Evidence

- PersonaObject schema (`scoring_weights`, `banding`, `tone`, `custom_rules`, `version`): (source: [[analyses/persona-agent-spec]] §Step 1 Output, [[concepts/persona-layer]] §PersonaObject fields)
- Default dimension weights (fit 25%, intent 25%, engagement 20%, behaviour 20%, context 10%): (source: [[concepts/signal-types]] §How Weights Work)
- Default bucket thresholds (hot_min 80, warm_min 55): (source: [[analyses/orchestration-layer-spec]] §bucket thresholds)
- `WEIGHT_SUM` and `THRESHOLD_ORDER` cross-field rules: (source: [[analyses/llm-io-contract]] §VALIDATION_RULES)
- Signal-level direct edit without re-run: (source: [[analyses/persona-agent-spec]] §When it does NOT run)
- Signal `weight_within_dim` field and sum-to-1.0 constraint per dimension: (source: [[analyses/persona-agent-spec]] §Step 3)
- `recommended_action` 7-value enum hardening: (source: [[analyses/llm-io-contract]] §OUTPUT_SCHEMA)
- Banding enforcement by Output Schema Layer (banding wins over LLM bucket): (source: [[analyses/rating-agent-spec]] §Component 4, [[analyses/llm-io-contract]] cross-field rule `BUCKET_SCORE_CONSISTENCY`)
- `tone` and `custom_rules` not in INPUT_SCHEMA `persona` object: (source: [[analyses/llm-io-contract]] §INPUT_SCHEMA properties)
- `custom_rules` usage for uncertainty flagging: (source: [[analyses/persona-agent-spec]] §Failure Handling)

---

## Caveats & Gaps

### Caveat 1 — Sub-Score Ceilings Conflict with Per-Tenant Weight Overrides

**This is a real inconsistency in the current spec.** The LLM I/O contract hardcodes `sub_scores` maximum values as schema validation ranges: fit max 25, intent max 25, engagement max 20, behaviour max 20, context max 10. These values are the default weights × 100.

If the Persona Agent infers a non-default weight set — say `scoring_weights.fit = 0.40` — the correct ceiling for `sub_scores.fit` becomes 40, not 25. But the current output schema rejects any `sub_scores.fit > 25`. This means either:
- Per-tenant weight overrides do not function end-to-end (the schema cap prevents the LLM from scoring into the override range)
- The LLM I/O contract's sub_scores maxima must be made dynamic per tenant (derived from `scoring_weights × 100`) rather than hardcoded

This is a `[TBD — requires team decision]` gap. Until resolved, any scoring_weights override that produces a sub-score ceiling other than 25/25/20/20/10 will be rejected by the Output Schema Layer validator.

### Caveat 2 — `tone` and `custom_rules` Are Stored But Not Wired in the LLM I/O Contract

`tone` and `custom_rules` are both present in the PersonaObject schema but absent from the `persona` object in the INPUT_SCHEMA of the LLM I/O contract. Their downstream path into the Rating Agent prompt is undocumented. Three possible resolutions:

1. Add them as fields to the `persona` input object in the LLM I/O contract
2. Document how they are injected via the Prompt Layer's static system message (if that's the actual path)
3. Confirm they are defined but not yet wired (stored for future use)

No path can be assumed without explicit spec work. This is a gap to resolve before Rating Agent implementation.

### Caveat 3 — `recommended_action` Enum — B2C Coverage Gap

The 7-value enum was designed with a B2B context as the primary frame of reference. `schedule_demo` and `send_pricing_deck` are actions natural to a B2B sales cycle; for a B2C consumer brand these actions may be irrelevant, misleading, or inapplicable. The open design decision (per-tenant enum extension via PersonaObject) is not resolved. Until resolved, B2C tenants receive the same action set as B2B tenants; the LLM is expected to select the closest applicable value from the global enum.

### Caveat 4 — Direct Signal Weight Edit Has No UI/API Defined

The asymmetry (signal weights can be edited without a re-run) is established in persona-agent-spec but no admin UI or API endpoint for this operation has been designed. Until such an interface exists, this capability exists only at the database level. A direct database edit without validation risks breaking the sum-to-1.0 constraint for the affected dimension.

### Caveat 5 — `cold_max` is Redundant Storage

`banding.cold_max` is always `warm_min − 1` and is derivable at runtime. It is stored as an explicit field in the PersonaObject. If a future update changes `warm_min` without also updating `cold_max`, the two fields will be inconsistent. Any Persona Agent re-run that produces a new `warm_min` must also write the derived `cold_max`. A system-level invariant check (cold_max == warm_min − 1) should be added to the PersonaObject validation path.

---

## Follow-up Questions

- Should sub-score ceilings in the LLM I/O contract be made dynamic (derived from `scoring_weights × 100` per tenant) rather than hardcoded? This is required for per-tenant weight overrides to function correctly.
- How do `tone` and `custom_rules` reach the Rating Agent? Through the structured input schema, through the static system prompt, or not at all yet?
- Should `recommended_action` be extendable per tenant via the PersonaObject? If yes, where is the tenant's allowed action set stored, and how does the LLM learn the tenant-specific enum at inference time?
- Should the admin UI for direct signal weight editing validate the sum-to-1.0 constraint inline before committing, or rely on an orchestrator-level pre-flight check?
- When a feedback-driven re-run executes ICP+Signal steps only (without Step 1), does `scoring_weights` and `banding` stay unchanged from the previous PersonaObject version? This partial re-run behavior is flagged as `[confirmed in governance spec]` but the exact scope is still TBD. (source: [[analyses/persona-agent-spec]] §Open Decisions)

---

## Related Documents

- [[analyses/client-config-schema-business-profile]] — Subtask 1: business profile fields (the inputs that drive Persona Agent inference)
- [[analyses/client-config-schema-defaults]] — Subtask 3: operational defaults and tier-linked limits
- [[analyses/persona-agent-spec]] — Persona Agent internals (how these fields are inferred, failure handling, re-run conditions)
- [[analyses/rating-agent-spec]] — Rating Agent (consumes scoring_weights, banding, tone via PersonaObject)
- [[analyses/llm-io-contract]] — LLM I/O contract (INPUT_SCHEMA persona object, OUTPUT_SCHEMA sub_scores and recommended_action)
- [[concepts/persona-layer]] — PersonaObject schema and Persona Engine loading behavior
- [[concepts/signal-types]] — Five scoring dimensions and default weights
- [[analyses/orchestration-layer-spec]] — Bucket threshold defaults and Disqualification Gate
