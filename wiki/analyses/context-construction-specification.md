---
type: analysis
question: "How is the complete LLM context assembled for each Rating Agent scoring call?"
date: 2026-05-18
tags: [context, llm, prompt-layer, orchestrator, caching, tenant-isolation, validation, token-budget]
sources_consulted:
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/prompt-template-framework]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/signal-detection-rule-spec]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/persona-layer]]"
status: COMPLETE
---

# Context Construction Specification

**System:** Multi-Tenant Adaptive Lead Intelligence Engine  
**Version:** 1.0.0  
**Date:** 2026-05-18

**Scope:** Rating Agent LLM context assembly — system message and user message construction, ownership, validation, token budget, and tenant isolation.

**Out of scope:** Prompt content and wording (see [[analyses/prompt-orchestration-framework]]), signal extraction logic (see [[analyses/signal-detection-rule-spec]]), LLM I/O schemas (see [[analyses/llm-io-contract]]).

---

## 1. What Is "Context" in This System

The LLM context is the complete payload sent to the model for each Rating Agent call. It has exactly two parts:

| Part | API field | Changes per | Cacheable |
|---|---|---|---|
| **System message** | `system` | Tenant + prompt version | Yes — provider caches after first call |
| **User message** | `messages[0]` | Lead | No — unique per lead |

**Rule:** Business logic, tenant configuration, and output format live in the system message. Lead data, signal values, and variant context live in the user message. Nothing crosses this boundary.

---

## 2. System Message — What It Contains and Who Owns It

The system message is assembled **once per tenant per prompt version** by the **Prompt Layer** (Intelligence Layer Component 2). The Orchestrator does not write the system message — it passes required data to the Prompt Layer and receives the assembled message back.

### 2.1 System Message Sections

| Section | Content | Source |
|---|---|---|
| `[SYSTEM]` | Role definition, scoring rubric, dimension weights, handling rules for missing signals | PersonaObject (scoring_weights) + locked scoring rules |
| `[CONTEXT]` | Tenant business description, ICP narrative, disqualifying profiles, per-signal weights | PersonaObject + IcpDefinition |
| `[OUTPUT FORMAT]` | JSON schema, field definitions, hard constraints (no markdown, JSON only) | Schema constants (system-defined) |

### 2.2 Immutability Rule

Once assembled for a given `(tenant_id, prompt_template_version)` pair, the system message is **immutable**. It is stored in `prompt_registry`. Any change to the PersonaObject or IcpDefinition that would alter the system message content must increment `prompt_template_version` — it must not mutate the stored message in place.

**Why:** Mutating a cached system message without version increment makes historical lineage unresolvable. The system cannot determine which prompt produced which score.

### 2.3 Cache Stability Rules

The system message cache breaks when any of the following change:
- `persona.scoring_weights` (any dimension weight)
- `persona.icp_summary` or `persona.disqualifying_profiles`
- Any signal definition (name, weight, or description)
- The scoring rubric (locked rules — requires schema version bump)

Any change must go through a `prompt_template_version` increment, not an in-place edit.

### 2.4 Signal Ordering

Signals within each dimension in the system message **must be sorted alphabetically by signal name.** This ensures the system message is byte-identical across calls for the same tenant/version, which is required for LLM provider caching.

The Prompt Layer enforces this sort. The signal order in the user message must match the system message order exactly.

---

## 3. User Message — What It Contains and Who Owns It

The user message is assembled **per lead, per call** by the **Prompt Layer**, using data prepared and passed by the **Orchestrator**.

### 3.1 User Message Sections

| Section | Content | Source |
|---|---|---|
| `VARIANT` label | `new` / `returning` / `rescore` | Orchestrator (from trigger context) |
| `LEAD DATA` | Normalised contact fields, company fields, channel, first_contact_date, city_tier | EnrichedLead (post-P1-3 Normalise) |
| `DATA COMPLETENESS` | Float 0.0–1.0 | `derived_metrics.lead_completeness` (set at P1-3) |
| `SIGNAL VALUES` | One line per signal: `<name> : <value>` | `signal_values` dict (set at P1-2b extraction) |
| Variant-specific section | Prior score + bucket (returning); prior score + feedback reason (rescore) | `context_inputs` from Orchestrator |

### 3.2 Signal Completeness Contract

**Every signal defined in the tenant's signal registry must appear in the user message signal values block, even if its value is `not_detected`.** A missing signal slot is an assembly error — not a valid "absent" state.

This contract is enforced by the Prompt Layer. If the `signal_values` dict is missing a signal key that exists in the tenant's signal registry, the Prompt Layer raises `PromptAssemblyError` and the call does not proceed.

---

## 4. Context Assembly — Ownership and Sequence

```
Orchestrator prepares:
  1. Loads PersonaObject via Persona Engine (cache → DB)
  2. Validates PersonaObject freshness (see §6)
  3. Receives EnrichedLead + signal_values dict (post-P1-2b and P1-3)
  4. Selects variant (new / returning / rescore)
  5. Loads context_inputs if variant ≠ new
  6. Passes all data to Prompt Layer

Prompt Layer assembles:
  7. Retrieves stored system message from prompt_registry (if exists for tenant/version)
       OR assembles and stores it (first call for this tenant/version)
  8. Assembles user message from EnrichedLead, signal_values, variant, context_inputs
  9. Enforces alphabetical signal sort in both message sections
  10. Runs pre-send validation gate (see §5)
  11. Returns assembled context to Orchestrator

Orchestrator calls LLM:
  12. Passes assembled context to Rating Agent component (Component 3)
```

**Owner boundary:** Steps 1–6 are the Orchestrator's responsibility. Steps 7–11 are the Prompt Layer's responsibility. The Orchestrator never writes prompt text directly.

---

## 5. Pre-Send Validation Gate

The Prompt Layer must pass all of the following checks before making the LLM API call. Any failure raises the specified error and aborts the call — no LLM cost is incurred on failure.

| Check | Failure condition | Error raised |
|---|---|---|
| All required input fields present | Missing required field | `PromptAssemblyError` |
| All tenant signals present in signal_values | Missing signal key | `PromptAssemblyError` |
| `persona.scoring_weights` sum to 1.0 (±0.001) | Sum ≠ 1.0 | `PersonaInvalidError` |
| `persona.warm_min < persona.hot_min` | Threshold inversion | `PersonaInvalidError` |
| Total token count ≤ context budget (see §7) | Context too large | `PromptTooLargeError` |
| `variant = new` → all `context_inputs` fields are null | Non-null prior context on new lead | `InputValidationError` |
| `variant = returning` → `prior_score`, `prior_bucket` non-null; `touchpoints` non-empty | Missing prior context | `InputValidationError` |
| `variant = rescore` → `feedback_reason` non-null | Missing feedback | `InputValidationError` |

`PersonaInvalidError` and `PersonaNotFoundError` are **hard failures** — lead routes to `human_review` immediately, admin alert fires. No retry.

All other errors: one retry after the Orchestrator corrects the input. If still failing: `ScoringFailure` → `human_review`.

---

## 6. Tenant Isolation Guarantees

1. **Namespace isolation:** `tenant_id` is required on every call. The Persona Engine loads only the PersonaObject for the given `tenant_id`.

2. **System message isolation:** System messages are keyed by `(tenant_id, prompt_template_version)`. A lookup for Tenant A cannot return Tenant B's system message.

3. **Signal registry isolation:** The signal completeness check validates against the signal registry for the specific `tenant_id`. Tenant A's signals are never injected into Tenant B's user message.

**PII rule:** Lead contact fields (name, phone, email) appear in the user message only. They are never included in the system message — PII is always in the non-cached, per-lead portion of the context.

---

## 7. Token Budget and Size Limits

Token budgets are set per tier in `tenant_config`. Proposed defaults:

| Context part | Starter | Growth | Enterprise |
|---|---|---|---|
| System message | 4 000 tokens | 6 000 tokens | 8 000 tokens |
| User message | 1 500 tokens | 2 000 tokens | 3 000 tokens |
| **Total** | **5 500 tokens** | **8 000 tokens** | **11 000 tokens** |

If the system message exceeds budget, `PromptTooLargeError` is raised. Resolution is a configuration fix (reduce signal count or shorten ICP text) — not a runtime retry.

**Hard limits on content length:**
- `persona.icp_summary`: max 2 000 characters (enforced in INPUT_SCHEMA)
- `persona.disqualifying_profiles`: max 10 items × 200 characters each

---

## 8. PersonaObject Freshness

The Persona Engine caches the PersonaObject with a **15-minute TTL**.

- Cache hit within TTL → use cached object
- Cache miss or TTL expired → reload from DB, refresh cache
- DB returns no PersonaObject for `tenant_id` → `PersonaNotFoundError` (hard failure, admin alert)

**Stale-on-re-run protection:** When the Persona Agent completes a re-run, it increments `persona_version` and writes the new PersonaObject to DB. In-flight scoring calls still holding the old cached version complete under the old version — this is accepted. Their `persona_version` in `lineage_record` identifies them correctly. The cache is not force-flushed; TTL expiry is the natural handover.

---

## 9. Versioning and Lineage

Every assembled context carries three version identifiers recorded in `lineage_record` after the call:

| Identifier | Source | Tracks |
|---|---|---|
| `prompt_template_version` | Loaded from `prompt_registry` | Which system message was used |
| `persona_version` | PersonaObject field | Which tenant configuration drove scoring |
| `schema_version` | System constant | Which output schema was expected |

These three identifiers make every scoring call fully attributable — the feedback loop uses `prompt_template_version` for pattern detection; governance uses `persona_version` to detect when re-runs are needed.

---

## 10. Error Summary

| Error | Trigger | Retry | Lead outcome |
|---|---|---|---|
| `PersonaNotFoundError` | No PersonaObject for tenant_id | No | `human_review`, admin alert |
| `PersonaInvalidError` | Weights ≠ 1.0 or threshold inversion | No | `human_review`, admin alert |
| `PromptAssemblyError` | Missing field or signal slot | 1 retry after correction | If still failing: `ScoringFailure` → `human_review` |
| `InputValidationError` | Variant/context_inputs mismatch | 1 retry | If still failing: `ScoringFailure` → `human_review` |
| `PromptTooLargeError` | Context exceeds token budget | No (config fix required) | `human_review`, tenant config alert |

---

## Open Decisions

| Decision | Status |
|---|---|
| Token budget values per tier | Proposed defaults above — confirm with engineering after first tenant onboarding |
| Force-flush Persona Engine cache on Persona Agent re-run completion | TBD — team decision; current spec uses TTL expiry |
| Max signal count per dimension | TBD per tenant during onboarding; affects system message token budget |
