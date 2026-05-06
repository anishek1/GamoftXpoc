---
type: analysis
question: "What are the business profile fields in the client configuration schema — covering industry, business model, geography, and target market?"
date: 2026-05-06
tags: [client-config, schema, business-profile, onboarding, tenant-setup, persona-layer]
sources_consulted:
  - "[[analyses/onboarding-flow-inputs]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[concepts/persona-layer]]"
  - "[[sources/2026-core-business-entities]]"
  - "[[concepts/signal-types]]"
status: COMPLETE — Subtask 1 of 3 (Persona and scoring preference fields in client-config-schema-persona-scoring; Default and override settings in client-config-schema-defaults)
---

# Client Configuration Schema — Business Profile Fields (Subtask 1 of 3)

**Question:** What are the business profile fields in the client configuration schema — covering industry, business model, geography, and target market?
**Date:** 2026-05-06

---

## Purpose of This Document

This document defines the **business profile section** of the client configuration schema. It specifies every field that describes what a client's business is, who they serve, and what markets they operate in.

These fields form the foundational input to the Persona Agent. Every LLM-based inference downstream — scoring weights, ICP definition, signal definitions — is derived from these fields. Getting this section right is the prerequisite for all intelligent behaviour in the system.

**What this section covers:** Who the client is, what they sell, who they sell to, and where they operate.

**What this section does NOT cover:**
- Scoring weights and dimension preferences → Subtask 2 (client-config-schema-persona-scoring)
- Operational limits, tier settings, LLM cost caps → Subtask 3 (client-config-schema-defaults)
- Channel connector configuration → [[analyses/channel-integration-layer]]
- Per-lead consent records → `consent_preference` entity, enforced at Pipeline 1 Consent Gate

---

## Answer / Finding

The business profile section has four field groups:

1. **User-Collected Fields** — entered by the client during Stage 3 of onboarding. These are the only fields the client directly controls.
2. **LLM-Inferred Business Context** — produced by Persona Agent Step 1. Derived from user-collected fields; never entered by the user.
3. **LLM-Inferred Target Market** — produced by Persona Agent Step 2 (ICP Definition). Defines the ideal buyer profile.
4. **System-Generated Fields** — created and managed by the platform. Not user-editable.

Every field is mapped to a storage entity from the Core Business Entity Catalog (source: [[sources/2026-core-business-entities]]).

---

## Group 1 — User-Collected Fields

Collected during onboarding Stage 3. These are the only fields the client fills in. See [[analyses/onboarding-flow-inputs]] §Stage 3 for the full form specification.

| Field | Type | Required | Validation | Storage Entity | Notes |
|-------|------|----------|------------|----------------|-------|
| `business_type` | `enum: B2B \| B2C \| Hybrid` | Required | Must be one of the three valid values | `business_profile` | Collected first; controls `target_audience` label on the form |
| `industry` | `string` | Required | 3–100 characters; free text at MVP | `business_profile` | Sector or vertical (e.g., "Industrial HVAC", "Organic Food D2C") |
| `business_description` | `string` | Required | 150–2000 characters | `business_profile_source` (raw) + `business_profile` (strengthened) | See dual-storage rule below |
| `target_audience` | `string[]` | Required | ≥1 entry; each entry ≤200 characters | `business_profile` | Label adapts per `business_type`; see mapping rule below |
| `geography_focus` | `string[]` | Required | ≥1 entry; each entry ≤100 characters | `business_profile` | The client's TARGET geographic market — not where the client is located |
| `negative_profiles` | `string[]` | Optional | May be empty; each entry ≤200 characters | `business_profile` | Profiles to exclude from scoring (e.g., "students", "job seekers") |

### Design Rule — `business_type` as Business Model

`business_type` (B2B / B2C / Hybrid) is the canonical classification for the client's **business model** in this schema.

A secondary operational model dimension (e.g., SaaS, marketplace, professional services, manufacturing) is **not collected as a separate form field**. The client embeds this in `business_description`. The Persona Agent infers the operational model from the description and uses it to calibrate `sales_cycle`, `ticket_size`, and `decision_complexity`.

**Rationale:** Asking clients to self-classify into an operational model taxonomy introduces enumeration errors (many clients do not use standard categories). Free-text description with LLM inference produces more accurate results. This is by design, not a gap.

### Design Rule — `target_audience` Storage Mapping

The form label `target_audience` adapts per `business_type`:
- `B2B` → *"Who are your ideal customers? (describe the companies and roles you sell to)"*
- `B2C` → *"Who are your ideal customers? (describe the type of person you sell to)"*
- `Hybrid` → *"Who are your ideal customers? (describe both the businesses and individuals you sell to)"*; requires ≥1 B2B entry AND ≥1 B2C entry

In storage (`business_profile`), the entries are written to the `target_roles` field (for B2B) or an equivalent target descriptor field (for B2C / Hybrid). The Persona Agent receives the raw entries and maps them into the PersonaObject's `target_roles` field.

### Design Rule — `business_description` Dual Storage

The `business_description` field goes through a strengthening step (P2-1 HYBRID) before the Persona Agent receives it:

```
User submits business_description
        │
        ▼ stored as-is
business_profile_source.raw_description   ← immutable; original user text
        │
        ▼ LLM strengthening call (P2-1)
business_profile.description              ← the version the Persona Agent sees
```

Both versions are stored permanently. The raw version enables audit and rollback. The strengthened version is what drives all downstream inference. Neither version is shown to the user after the confirmation screen.

### Design Rule — `geography_focus` Meaning

`geography_focus` captures the client's **target market geography** — the regions where their intended buyers or customers are located. It is not the client's own operating location.

Example: An Indian edtech company that sells to UK universities sets `geography_focus = ["United Kingdom"]`, not `["India"]`.

If both are relevant (multinational business), multiple entries are valid (e.g., `["India", "Southeast Asia", "UAE"]`).

---

## Group 2 — LLM-Inferred Business Context Fields

Produced by **Persona Agent Step 1** (Business Persona LLM call). These fields are never collected from the user. They are inferred from the Group 1 fields. See [[analyses/persona-agent-spec]] §Step 1 for inference logic.

**Rule:** No onboarding form field, no admin panel, and no API endpoint should allow direct user input into these fields. They are owned by the Persona Agent.

| Field | Type | Inference Source | Validation | Storage Entity |
|-------|------|-----------------|------------|----------------|
| `sales_cycle` | `enum: Short \| Medium \| Long` | `business_type`, `industry`, `business_description` | Must be one of three values | `personas` (PersonaObject) |
| `ticket_size` | `enum: Low \| Medium \| High` | `business_description`, `target_audience` | Must be one of three values | `personas` (PersonaObject) |
| `decision_complexity` | `enum: Single \| Multi-stakeholder` | `business_type`, `target_audience` | Must be one of two values | `personas` (PersonaObject) |
| `product_lines` | `string[]` | `business_description` | May be empty if not inferable | `personas` (PersonaObject) |

**What these fields mean:**
- `sales_cycle` — how long a typical deal takes to close; influences urgency interpretation in lead scoring
- `ticket_size` — average deal value band; influences how budget signals are weighted
- `decision_complexity` — whether a single contact can close or multiple stakeholders are needed; influences authority signals
- `product_lines` — the distinct products or service offerings; used to resolve ambiguous product references in lead messages

**Failure rule:** If the Persona Agent cannot infer a required field with sufficient confidence, it leaves the field unset (not null — it writes a `null` with an explicit note in the `custom_rules` list so the team lead knows to supplement). It never fabricates a value. (source: [[analyses/persona-agent-spec]] §Failure Handling)

---

## Group 3 — LLM-Inferred Target Market Fields (ICP Definition)

Produced by **Persona Agent Step 2** (ICP Definition LLM call). These define the ideal buyer profile in concrete terms. The Persona Agent receives the Group 2 output (PersonaObject) as input and produces the IcpDefinition.

These fields are stored in `ideal_customer_profile` and also embedded inside the PersonaObject for zero-latency loading at scoring time.

| Field | Type | Description | Storage Entity |
|-------|------|-------------|----------------|
| `icp_description` | `string` | Narrative description of the ideal buyer | `ideal_customer_profile` |
| `target_segment.industry` | `string` | Target buyer's industry | `ideal_customer_profile` |
| `target_segment.company_size` | `string` | Target company size range (for B2B) | `ideal_customer_profile` |
| `target_segment.geography` | `string` | Buyer's expected geography (aligned with `geography_focus`) | `ideal_customer_profile` |
| `target_segment.role_profile` | `string` | Decision-maker or influencer role description | `ideal_customer_profile` |
| `company_size_preference` | `string[]` | e.g., `["SME", "Enterprise"]` — which company sizes are in scope | `ideal_customer_profile` |
| `priority_signals` | `string[]` | Which signals most strongly indicate a match with this ICP | `ideal_customer_profile` |
| `disqualifying_signals` | `string[]` | What immediately eliminates a lead regardless of other signals | `ideal_customer_profile` |
| `buying_triggers` | `string[]` | External events that indicate sudden high-purchase readiness | `ideal_customer_profile` |
| `icp_examples` | `string[]` | Concrete examples of ideal leads (optional; aids scoring calibration) | `ideal_customer_profile` |

**Cross-system note:** `disqualifying_signals` directly feeds the Disqualification Gate in Pipeline 1. Any string in this list is automatically compared against enriched lead data during the gate evaluation step. See [[analyses/orchestration-layer-spec]] §Disqualification Gate. This makes the ICP definition operationally active — not just descriptive.

---

## Group 4 — System-Generated Fields

Created and updated by the platform. These are not exposed as inputs.

| Field | Type | Set By | Description | Storage Entity |
|-------|------|--------|-------------|----------------|
| `business_profile_id` | `UUID` | System on creation | Unique identifier for this profile | `business_profile` |
| `tenant_id` | `UUID` | System on creation | Multi-tenant scope key; inherited from org setup | `business_profile` |
| `profile_status` | `enum: draft \| active \| archived` | System | `draft` during onboarding; `active` after Persona Agent completes; `archived` on re-run (previous version) | `business_profile` |
| `profile_version` | `integer` | System | Starts at 1; increments on each Persona Agent re-run | `business_profile_version` |
| `created_at` | `timestamp` | System | When the profile record was first created | `business_profile` |
| `updated_at` | `timestamp` | System | When the profile was last modified | `business_profile` |
| `persona_agent_run_id` | `UUID` | System | Links this profile version to the specific Persona Agent run that produced it | `business_profile_version` |

**Version tracking rule:** `profile_version` increments when the Persona Agent successfully completes a full run (new onboarding OR approved re-run). It does not increment when individual user-editable fields are updated in isolation. A version bump always corresponds to a Persona Agent re-run — this preserves the requirement that every version has a complete, consistent PersonaObject backing it.

---

## Field Relationship Summary

```
Stage 3 User Input
┌──────────────────────────────────────────────────┐
│ business_type (enum)       ─────────────────────►│
│ industry (string)           ────────────────────►│
│ business_description (str)  ──► P2-1 LLM ──────►│  Persona Agent Step 1
│ target_audience (string[])  ────────────────────►│  ─────────────────────►  PersonaObject
│ geography_focus (string[])  ────────────────────►│      sales_cycle         (stored in personas)
│ negative_profiles (str[])   ────────────────────►│      ticket_size
└──────────────────────────────────────────────────┘      decision_complexity
                                                           product_lines
                                                                │
                                                                ▼
                                                    Persona Agent Step 2
                                                    ─────────────────────►  IcpDefinition
                                                        target_segment       (stored in
                                                        company_size_pref    ideal_customer_profile)
                                                        priority_signals
                                                        disqualifying_sigs
                                                        buying_triggers
```

---

## Required vs Optional Summary

| Field | Required | Default if Not Provided |
|-------|----------|------------------------|
| `business_type` | Required | None — blocks Stage 3 submission |
| `industry` | Required | None — blocks Stage 3 submission |
| `business_description` | Required | None — blocks Stage 3 submission |
| `target_audience` | Required (≥1 entry) | None — blocks Stage 3 submission |
| `geography_focus` | Required (≥1 entry) | None — blocks Stage 3 submission |
| `negative_profiles` | Optional | Empty list `[]` |
| All LLM-inferred fields | N/A — inferred | Left unset if insufficient input; flagged in `custom_rules` |
| All system-generated fields | N/A — auto-created | Set by system on events |

---

## Evidence

- Stage 3 form fields, validation rules, and `target_audience` label adaptation: (source: [[analyses/onboarding-flow-inputs]] §Stage 3)
- `business_description` dual storage (raw in `business_profile_source`, strengthened in `business_profile`) and P2-1 HYBRID step: (source: [[analyses/onboarding-flow-inputs]] §LLM-Strengthening Step)
- PersonaObject field schema (Step 1 output) including `sales_cycle`, `ticket_size`, `decision_complexity`, `product_lines`: (source: [[analyses/persona-agent-spec]] §Step 1)
- IcpDefinition schema (Step 2 output) including `target_segment`, `priority_signals`, `disqualifying_signals`: (source: [[analyses/persona-agent-spec]] §Step 2)
- `business_profile`, `business_profile_source`, `ideal_customer_profile`, `business_profile_version` entity definitions: (source: [[sources/2026-core-business-entities]])
- `business_type` → scoring behavior coupling and competitive moat framing: (source: [[concepts/persona-layer]])
- Disqualification Gate connection to `disqualifying_signals`: (source: [[analyses/orchestration-layer-spec]] §Disqualification Gate)

---

## Caveats & Gaps

- **`industry` is free text at MVP.** A controlled vocabulary (dropdown or typeahead) would improve Persona Agent inference consistency across tenants. Logged as a future improvement in [[analyses/onboarding-flow-inputs]] §Caveats. Not a blocking issue at current scale.
- **`geography_focus` is free text at MVP.** A structured country/region selector would enable geo-based analytics and filtering. Same future improvement note applies.
- **Operational model (SaaS vs services vs marketplace) is not a separate field.** It is embedded in `business_description` and inferred by the Persona Agent. If future analytics require explicit business model classification, a `business_model` field can be added as an optional enum without breaking any existing logic.
- **`target_audience` for B2C tenants.** The `target_roles` field in PersonaObject uses role names (CTO, Director) which are B2B terminology. For B2C tenants, the Persona Agent translates `target_audience` entries into equivalent demographic or psychographic descriptors. The field name `target_roles` in the PersonaObject is a legacy naming issue — it stores both B2B roles and B2C audience profiles.
- **`negative_profiles` vs `disqualifying_signals` distinction.** `negative_profiles` is collected from the user (blunt exclusion list). `disqualifying_signals` is produced by the Persona Agent (more precise, contextually derived). They serve the same operational purpose (feed the Disqualification Gate) but are at different levels of specificity. The Persona Agent uses `negative_profiles` as a seed to produce more precise `disqualifying_signals`.

---

## Follow-up Questions

- Should `geography_focus` eventually distinguish between "where the client sells" (target market) and "where the client's buyers physically are" (delivery geography)? Currently treated as the same.
- At what point should `industry` become a controlled vocabulary? After Month 1 with 3+ tenants, common mismatches across free-text industry values would be visible.
- Should the system ever allow a team lead to manually override an LLM-inferred field (e.g., change `ticket_size` from Low to High without a full Persona Agent re-run)? Currently the design requires a re-run. Direct field override is simpler but bypasses the consistency guarantee.

---

## Related Documents

- [[analyses/client-config-schema-persona-scoring]] — Subtask 2: persona options, scoring weight preferences, output format preferences
- [[analyses/client-config-schema-defaults]] — Subtask 3: default values and override behavior for operational settings
- [[analyses/onboarding-flow-inputs]] — Stage 3 form specification (the user-input view of Group 1 fields)
- [[analyses/persona-agent-spec]] — Persona Agent internals (how LLM-inferred fields are produced)
- [[concepts/persona-layer]] — PersonaObject schema and Persona Engine loading behavior
- [[sources/2026-core-business-entities]] — Authoritative entity catalog (storage backing for all groups)
- [[analyses/orchestration-layer-spec]] — Disqualification Gate (consuming `disqualifying_signals`)
