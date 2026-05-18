---
type: analysis
question: "How are tenant personas structured, validated, classified by quality, and used to classify leads for scoring?"
date: 2026-05-18
tags: [persona, classification, persona-object, icp, quality, signal-coverage, versioning, custom-rules, lifecycle]
sources_consulted:
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/adaptive-scoring-strategy-b2b-b2c]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/prompt-orchestration-framework]]"
  - "[[concepts/persona-layer]]"
  - "[[concepts/signal-types]]"
status: COMPLETE
---

# Persona Classification Framework

**System:** Multi-Tenant Adaptive Lead Intelligence Engine  
**Version:** 1.0.0  
**Date:** 2026-05-18

**Scope:** The PersonaObject schema, persona quality criteria, minimum signal coverage requirements, ICP specificity standards, custom rules format, the `tone` field, persona change classification, staleness detection, and how personas are used to classify leads at scoring time.

**Relationship to persona-agent-spec:** [[analyses/persona-agent-spec]] covers the process of creating a persona (Persona Agent Steps 1–3). This document covers the structure and quality of what is produced, and how it is used for lead classification. Both documents are required.

---

## 1. What Is a Persona in This System

A **persona** is the complete, structured representation of a tenant's business identity and ideal customer profile, stored in the `personas` table as a `PersonaObject`. It is the only piece of tenant-specific configuration that flows into every single scoring call for that tenant.

The PersonaObject has three jobs:
1. **Tell the LLM who the tenant is** — the ICP summary and business description in the system message
2. **Configure the scoring engine** — dimension weights, bucket thresholds, signal definitions
3. **Drive lead classification** — the ICP's disqualifying profiles and priority signals determine how the LLM classifies each lead

A persona that is vague, incomplete, or internally inconsistent produces unreliable scores for every lead. Persona quality is the highest-leverage configuration in the system.

---

## 2. PersonaObject — Full Schema

```json
{
  "tenant_id":             "uuid — required",
  "persona_version":       "string semver e.g. 'v1.2.0' — required",
  "business_type":         "'B2B' | 'B2C' — required; locked for this version",
  "industry":              "string — required; tenant's primary sector",
  "business_description":  "string 50–1000 chars — required; plain-language description of what the business does and sells",
  "target_roles":          "string[] — required for B2B; job titles or role profiles of decision-makers/influencers",
  "company_size_preference": "['SME', 'Enterprise'] — required for B2B; array of preferred company size buckets",
  "geography_focus":       "string[] — required; list of regions, cities, or city tiers in scope",
  "sales_cycle":           "'Short' | 'Medium' | 'Long' — required; typical time from first contact to close",
  "ticket_size":           "'Low' | 'Medium' | 'High' — required; typical deal value",
  "decision_complexity":   "'Single' | 'Multi-stakeholder' — required",
  "product_lines":         "string[] — optional; list of product/service categories",
  "negative_profiles":     "string[] — required; explicit lead profiles to exclude",
  "scoring_weights": {
    "fit":        "float 0.0–1.0",
    "intent":     "float 0.0–1.0",
    "engagement": "float 0.0–1.0",
    "behaviour":  "float 0.0–1.0",
    "context":    "float 0.0–1.0"
  },
  "banding": {
    "hot_min":  "integer 1–100",
    "warm_min": "integer 1–100"
  },
  "icp": "IcpDefinition — embedded; see §3",
  "custom_rules": "string[] — optional; see §5",
  "tone": "'formal' | 'conversational' | 'technical' — optional; default 'conversational'; see §6",
  "inference_flags": "object — system-generated; records low-confidence inferred fields; see §7",
  "created_at":  "timestamptz",
  "created_by":  "'persona_agent' | 'manual_override'"
}
```

**Invariants enforced at creation:**
- `scoring_weights` must sum to 1.0 (±0.001)
- `banding.warm_min < banding.hot_min`
- `business_type` must match `applicable_to` on all signals in the tenant's signal registry
- `negative_profiles` must not be empty (at least one exclusion profile required)

---

## 3. IcpDefinition — Full Schema

The IcpDefinition is embedded inside the PersonaObject and also stored in the `ideal_customer_profile` table for independent versioning.

### B2B IcpDefinition
```json
{
  "icp_description":     "string 50–500 chars — narrative of ideal buyer",
  "target_segment": {
    "industry":        "string — primary industry of target companies",
    "company_size":    "string — e.g. '50–500 employees'",
    "funding_stage":   "string or null — e.g. 'Series A–C'",
    "geography":       "string — matches persona.geography_focus",
    "role_profile":    "string — decision-maker titles"
  },
  "priority_signals":      "string[] — signal names that most predict conversion; ≥2 required",
  "disqualifying_signals": "string[] — signal names that eliminate a lead regardless of score; ≥1 required",
  "buying_triggers":       "string[] — external events that raise conversion likelihood; ≥1 recommended",
  "icp_examples":          "string[] — optional 1–3 concrete example lead descriptions"
}
```

### B2C IcpDefinition
```json
{
  "icp_description":     "string 50–500 chars",
  "target_segment": {
    "interest_category": "string",
    "demographic":       "string",
    "geography":         "string",
    "purchase_frequency": "string or null"
  },
  "priority_signals":      "string[] — ≥2 required",
  "disqualifying_signals": "string[] — ≥1 required",
  "buying_triggers":       "string[] — ≥1 recommended",
  "icp_examples":          "string[] — optional"
}
```

---

## 4. Persona Quality Criteria

A PersonaObject is **production-ready** if and only if it meets all of the following criteria. These are checked automatically at pipeline 2 completion before the persona is written to `prompt_registry`.

### 4.1 Completeness Criteria

| Field | Requirement | Why |
|---|---|---|
| `business_description` | ≥ 50 characters, specific (not generic like "we sell things") | Vague description produces vague ICP |
| `industry` | Must be a recognisable industry string (not "misc" or "other") | Signal applicability depends on industry |
| `negative_profiles` | ≥ 1 entry, each ≥ 10 characters | A persona without exclusions scores everyone too high |
| `icp.icp_description` | ≥ 50 characters | The ICP narrative drives the CONTEXT section of the scoring prompt |
| `icp.priority_signals` | ≥ 2 signal names; each name must exist in the tenant's signal registry | Priority signals drive higher signal weights in scoring |
| `icp.disqualifying_signals` | ≥ 1 signal name from signal registry | Disqualification Gate reads from this list |
| `scoring_weights` | Sum to 1.0 ± 0.001 | Mathematical constraint for correct scoring |
| Signal coverage | See §4.2 | Ensures all dimensions have scoring power |

### 4.2 Signal Coverage Requirements

A persona must have at least the minimum number of signals per dimension:

| Dimension | Minimum signals | Maximum signals (soft limit) |
|---|---|---|
| Fit | 3 | 6 |
| Intent | 5 | 10 |
| Engagement | 4 | 8 |
| Behaviour | 3 | 6 |
| Context | 2 | 5 |

**Why minimums matter:** A dimension with fewer than the minimum signals has insufficient scoring resolution. For example, a Fit dimension with only 1 signal means every lead either fully matches or fully fails Fit — there is no gradient.

**Why soft maximums matter:** More signals = longer system message = higher token cost + risk of exceeding token budget. See [[analyses/context-construction-specification]] §7.

**Validation:** The Prompt Layer checks signal count per dimension when generating the system message. Fewer than the minimum triggers a `PersonaInvalidError` with a specific message: `"Persona validation failed: Intent dimension has only 3 signals; minimum is 5."` The Persona Agent must re-run Step 3 with explicit instruction to add more signals.

### 4.3 ICP Specificity Check

A high-quality ICP can eliminate at least 50% of inbound leads as poor fit based on ICP criteria alone. An ICP that only eliminates 5% is too broad to be useful.

This is not measured at creation time (no lead data exists). It is measured after Month 1 using the **Disqualification Rate** metric (what % of leads are disqualified by the gate). If disqualification rate is < 5%, the team lead is alerted to review and tighten the ICP.

---

## 5. Custom Rules — Format and Enforcement

`PersonaObject.custom_rules` is a list of strings. Each string is a **plain-language rule** that the LLM must apply during scoring, above and beyond the standard rubric.

**Examples:**
```json
"custom_rules": [
  "If the lead mentions a competitor by name (Salesforce, HubSpot), treat it as a strong buying trigger and increase Intent score.",
  "Leads from outside India must have explicitly mentioned interest in international shipping — do not score serviceability as true otherwise.",
  "A lead that has already purchased once in the past 6 months is a priority for re-engagement — treat prior_customer=true as a 1.3x multiplier on the Behaviour dimension."
]
```

**Format rules:**
- Each rule must be ≥ 20 characters (filter out placeholder text)
- Maximum 10 custom rules per persona (keeps system message size manageable)
- Rules are injected at the bottom of the `[CONTEXT]` section in the system message, under the heading `CUSTOM SCORING RULES FOR THIS TENANT`
- Rules are plain English instructions to the LLM — they must be phrased as imperatives ("treat X as Y", "if X then Y")

**What custom rules cannot do:**
- Override the output schema (cannot instruct the LLM to add extra fields to the JSON)
- Override the bucket thresholds (thresholds are enforced deterministically by the Output Schema Layer)
- Override the scoring dimension weights (weights are structural — not modifiable per-call)

**Enforcement:** Custom rules are LLM instructions, not code. They are enforced by the LLM following the prompt. Compliance is checked during evaluation (Step 5: Reasoning Quality) — reviewers verify that custom rules are reflected in the scoring rationale when the rule conditions are met.

---

## 6. The `tone` Field

`PersonaObject.tone` controls the style of the `recommended_action` and `reasoning.salesperson_note` outputs.

| Tone value | Effect on `salesperson_note` | Effect on `recommended_action` enum |
|---|---|---|
| `formal` | Formal language, industry terminology, full sentences | No effect — enum values are fixed |
| `conversational` | Casual, direct language, action-oriented | No effect |
| `technical` | Technical language, metric references, data-driven framing | No effect |

**Scope:** `tone` only affects the free-text output fields (`reasoning.salesperson_note`). It does not change scoring logic, dimension weights, or which signals are prioritised. The `recommended_action` enum is fixed across all tenants (see [[analyses/llm-io-contract]]).

**Implementation:** The `tone` value is injected into the `[SYSTEM]` section of the prompt: `"Write all notes in a <tone> style appropriate for a <business_type> sales team."`

---

## 7. Inference Confidence Flags

When the Persona Agent infers a field that the tenant did not explicitly provide, it records the inferred field in `PersonaObject.inference_flags`. This allows the team lead to review and correct low-confidence inferences before activating the persona.

```json
"inference_flags": {
  "sales_cycle":       { "inferred": true, "confidence": "medium", "basis": "B2B SaaS companies typically have Medium sales cycles" },
  "ticket_size":       { "inferred": true, "confidence": "low", "basis": "Pricing not mentioned in business description; assumed Medium" },
  "geography_focus":   { "inferred": false }
}
```

**Confidence levels:**
- `high`: Inferred from clear evidence in the business description
- `medium`: Reasonable inference, but the description was ambiguous
- `low`: Insufficient evidence; team lead should explicitly confirm this field

**Validation at activation:** If any field has `confidence = "low"`, the persona activation requires team lead sign-off on that specific field (standard approval gates cover all fields, but low-confidence flags must be explicitly acknowledged). The team lead can correct a low-confidence field by submitting a correction that triggers a `patch` version update.

---

## 8. Persona Change Classification

When a re-run is proposed, the team lead must understand what type of change is happening. Changes are classified into three tiers:

| Change type | Tier | Prompt version impact | Example |
|---|---|---|---|
| Business description updated, same industry and ICP | Minor | MINOR version increment | "We now also serve healthcare clients in addition to SaaS" |
| ICP target segment changed significantly | Minor | MINOR version increment | Target company size expanded from 50–200 to 50–500 employees |
| Scoring weights adjusted | Minor | MINOR version increment | Reduced Fit weight from 0.25 to 0.20, increased Intent to 0.30 |
| New signal added to a dimension | Minor | MINOR version increment | New signal `tender_document_request` added to Intent |
| Signal removed | Minor | MINOR version increment + historical re-score recommended | Signal `website_visits` removed from Engagement |
| business_type changed | **Major** | New persona from scratch (full Pipeline 2 re-run) | Tenant pivoting from B2B to B2C model |
| Scoring rubric changed (system-level) | **Major** | Engineering deployment + all tenants' next re-run | Output schema version bump |
| ICP completely replaced (new target market) | **Major** | Full re-run required | New product line for entirely different customer segment |

**Rule:** Tier changes are classified by the Governance Layer when a re-run is proposed. Minor-tier changes allow selective Pipeline 2 re-run (ICP + Signal steps only, skipping Persona Step 1 if business description is stable). Major-tier changes require full Pipeline 2 from Step 1.

---

## 9. Persona Staleness Detection

A persona becomes stale when it no longer accurately reflects the tenant's business reality. The system detects staleness through three signals:

| Staleness signal | Detection mechanism | Response |
|---|---|---|
| **Scoring quality degradation** | AP2 (Monotonicity) or C5 (Signal Contribution Consistency) drops below threshold | Feedback loop proposes re-run to team lead |
| **High disqualification rate** | > 40% of leads are disqualified (ICP too narrow) | Governance layer flags; team lead reviews ICP |
| **Low disqualification rate** | < 5% of leads are disqualified (ICP too broad) | Governance layer flags; team lead reviews ICP |
| **Proactive check-in** | Scheduled check-in cadence (TBD: 2-week or monthly) | Team lead confirms whether business has changed |
| **Explicit team lead flag** | Team lead reports that scoring is no longer accurate | Direct re-run trigger |

**Staleness is not an automatic re-run trigger.** The system proposes; the team lead approves. See [[analyses/persona-agent-spec]] §Invocation Conditions.

---

## 10. How Personas Are Used for Lead Classification at Scoring Time

At scoring time, the PersonaObject classifies each lead by providing the LLM with:

1. **The ICP as a classification reference:** The `icp_summary` and `disqualifying_profiles` in the `[CONTEXT]` section tell the LLM exactly who fits and who doesn't.

2. **Dimension weights as classification priorities:** Higher weights signal to the LLM which dimensions matter most for this tenant's classification (e.g., for a short-cycle B2C tenant, Behaviour weight is 0.25 — the LLM knows purchase history is the primary classifier).

3. **Signal definitions as classification criteria:** Each signal is a specific yes/no (or graded) question about the lead. Together, they operationalise the ICP as a checklist.

4. **Custom rules as classification overrides:** Rules in `custom_rules` allow the tenant to define classification shortcuts (e.g., "competitor mention = strong intent regardless of other signals").

**Lead classification output:** The `reasoning.signal_contributors` array in the output shows exactly which signals classified this lead positively or negatively, and with what weight. This is the machine-readable audit trail of how the persona drove this specific lead's classification.

---

## Open Decisions

| Decision | Status |
|---|---|
| Minimum signal coverage enforcement: hard block vs warning | Proposed as hard block above — confirm after Phase 0 data shows whether Persona Agent reliably hits minimums |
| `inference_flags` format in PersonaObject | Proposed schema above — confirm with backend; needs a `jsonb` column in `personas` table |
| Proactive check-in cadence | TBD — 2-week or monthly; team decision after Month 1 |
| Disqualification rate thresholds (< 5% = too broad, > 40% = too narrow) | Proposed — adjust after Phase 0 baseline |
| Whether to support partial re-run (ICP + Signal only, skip Step 1) | Currently: Minor-tier changes allow selective re-run. Needs implementation decision. |
