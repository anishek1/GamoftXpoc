---
type: analysis
question: "What are the default values and client override behavior for operational settings in the client configuration schema?"
date: 2026-05-07
tags: [client-config, schema, defaults, tiering, tenant-config, operational-limits, overrides, system-config]
sources_consulted:
  - "[[analyses/service-scaling-strategy]]"
  - "[[analyses/llm-operational-safeguards]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/execution-type-classification]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[sources/2026-core-business-entities]]"
  - "[[analyses/governance-observability-layer]]"
status: COMPLETE — Subtask 3 of 3 (Business profile fields in client-config-schema-business-profile; Persona/scoring fields in client-config-schema-persona-scoring)
---

# Client Configuration Schema — Default and Override Settings (Subtask 3 of 3)

**Question:** What are the default values and client override behavior for operational settings in the client configuration schema?
**Date:** 2026-05-07

---

## Plain-English Summary

**Why this exists:** The platform serves multiple clients simultaneously on shared infrastructure. Without limits, one client could run thousands of AI calls per hour, spike costs for everyone, and slow the system down. This document defines the guardrails — how many AI calls each client can run, how much they can spend per day, and how much data they can process per request.

**Where it fits:** These settings live in the `tenant_config` database record, which is loaded at the start of every lead scoring run. They sit between the client's account setup and the actual pipeline execution — the pipeline checks these limits before doing any AI work. They're also the mechanism for the three-tier subscription model (basic / standard / premium).

**How it works:** Every client is assigned a tier when they sign up (default: basic). The tier sets automatic defaults for all limits. Some limits can be adjusted by the client's admin or the platform team within the tier's allowed range — for example, a client can voluntarily lower their own daily spending cap below the tier default, but cannot raise it above it. Changes take effect immediately on the next scoring run, with no cache delay. A separate system-level config applies across all clients as a final safety net.

---

## Purpose of This Document

This document defines the **operational settings section** of the client configuration schema. It specifies every per-tenant limit field, the tiering framework that drives defaults, which settings can be overridden and by whom, how overrides are enforced, and the system-wide settings that apply across all tenants.

**What this section covers:**
- Tier assignment and the `tenant_config` entity schema
- Per-tenant operational limits: concurrency, throughput, cost, token budget, API rate limits, reporting schedule, quality gate
- Infrastructure settings (pool vs silo)
- LLM model and prompt version configuration (partially open decisions)
- System-wide `system_config` settings
- Override rules: who can change what, within what bounds, and when changes take effect

**What this section does NOT cover:**
- Business profile fields (industry, business_type, geography) → [[analyses/client-config-schema-business-profile]]
- Scoring weights, banding thresholds, signal weights → [[analyses/client-config-schema-persona-scoring]]
- Channel connector configuration → [[analyses/channel-integration-layer]]
- Per-lead consent records → `consent_preference` entity, enforced at Pipeline 1 Consent Gate
- Security settings (RLS, JWT, RBAC role definitions) → [[analyses/governance-observability-layer]]

---

## Answer / Finding

Operational settings are split across two entities:

1. **`tenant`** — holds identity and commercial tier. The `tier` field is the master key that drives all defaults.
2. **`tenant_config`** — holds the effective operational limits for each tenant. Created when a tenant is activated; populated from tier defaults; overridable within bounds by authorized roles.

A third entity, **`system_config`**, holds platform-wide settings that apply to all tenants and are not overridable per-tenant.

**Entity catalog gap:** Four entities are absent from the 32-entity catalog from [[sources/2026-core-business-entities]]: `tenant_config`, `system_config`, `provider_pricing_config` (all introduced by this document), and `prompt_registry` (well-established in 6+ vault documents but missing from the catalog). All four need to be added. Additionally, `tenant` needs one field added (`tier`). See §Entity Gaps.

---

## Part 1 — The Two-Entity Model

### `tenant` — Identity and Tier

The `tenant` entity already exists in the 32-entity catalog (Group A, Core Lead Lifecycle). This document adds one field to it: **`tier`**.

| Field | Type | Notes |
|-------|------|-------|
| `tenant_id` | UUID | PK |
| `organization_name` | string | Set at onboarding Stage 2 |
| `organization_slug` | string | Unique slug; set at Stage 2 |
| `status` | enum: `onboarding \| active` | One-way transition; full state machine in [[analyses/onboarding-flow-readiness]] |
| **`tier`** | **enum: `basic \| standard \| premium`** | **The commercial tier; drives all `tenant_config` defaults** |
| `created_at` | timestamp | System |
| `updated_at` | timestamp | System |

**Sourcing note on this table:** The entity catalog names the `tenant` entity but does not define its field schema. The fields above are assembled from: `organization_name` / `organization_slug` → [[analyses/onboarding-flow-inputs]] §Stage 2; `status` → [[analyses/onboarding-flow-readiness]] §tenant.status State Machine; `created_at` / `updated_at` → standard platform fields; `tier` → added by this document. The only official vault source for `status` enum values is the state machine in [[analyses/onboarding-flow-readiness]], which defines two states: `onboarding` and `active` (one-way transition, no further states documented). `suspended` and `churned` are not in the vault and should not be included in this schema.

**`tier` rules:**
- Set to `basic` on tenant creation.
- Can only be changed by a **platform admin** — not a tenant admin, not a team lead.
- Changing tier triggers a `tenant_config` re-population from the new tier's defaults. Existing overrides that fall within the new tier's bounds are preserved; overrides that would exceed the new tier's bounds are discarded and the default applied.
- `tier` is the only field on `tenant` that Subtask 3 concerns itself with.

---

### `tenant_config` — Operational Settings

`tenant_config` is a **new entity** not currently in the 32-entity catalog. It is a one-to-one extension of `tenant` (FK `tenant_id`, unique constraint).

**Why a separate entity, not columns on `tenant`:**
- `tenant_config` changes more frequently than `tenant` (admins tune limits month-to-month; tenant identity rarely changes).
- RBAC scope: a team lead may have permission to modify certain `tenant_config` fields (e.g., `needs_review_threshold`) but should never be able to modify `tenant` identity fields. Separation makes the permission boundary clean.
- Audit trail: changes to operational limits are a different log class from changes to tenant identity.
- Golding (source: [[analyses/service-scaling-strategy]] §Tiering) explicitly recommends writing the per-tenant config structure as a first-class record so that tier changes are config changes, not code changes.

**Creation:** A `tenant_config` record is created automatically when `tenant.status` transitions to `active`. Initial values are populated from the tenant's tier defaults.

**Loading:** The orchestrator loads `tenant_config` at Pipeline 1 pre-flight (P1-0d Context Loading) alongside `persona` and `signal_definitions`. These are separate DB reads and separate context keys. (source: [[analyses/execution-type-classification]] P1-0d)

---

## Part 2 — `tenant_config` Field Definitions

Fields are grouped by functional area. For each field: type, tier defaults (Basic / Standard / Premium), who can override, and override bounds.

---

### Group 1 — Pipeline Execution Limits

These fields control how much throughput a single tenant can consume on the shared pipeline infrastructure.

| Field | Type | Basic | Standard | Premium | Overridable By | Override Bounds |
|-------|------|-------|----------|---------|----------------|-----------------|
| `scoring_concurrency_cap` | int | 2 | 3 | 5 | Platform admin | Cannot exceed tier max; can be lowered. **[PROPOSED — no minimum floor specified in vault]** |
| `pipeline_runs_per_hour` | int \| null | 20 | 50 | `null` (unlimited) | Platform admin | Cannot exceed tier max; can be lowered; `null` = unlimited |

**`scoring_concurrency_cap` scope:** This cap applies specifically to the **Sonnet (Rating Agent) calls** — the primary LLM call in `score_lead()`. Implementation: a semaphore keyed on `tenant_id`; before calling `score_lead()`, acquire the semaphore for that tenant. (source: [[analyses/service-scaling-strategy]] Recommendation 6; [[analyses/rating-agent-spec]] Per-Tenant Concurrency Cap)

**Gap:** The **Haiku (Message Parser)** call on the DM path is a separate, cheaper LLM call that fires before the Rating Agent. Whether it shares the same `scoring_concurrency_cap` semaphore or has its own independent cap is not resolved in existing documentation. The safe MVP default is to include it under the same cap; this prevents combined DM-path calls from inflating concurrency unexpectedly.

**`pipeline_runs_per_hour` null semantics:** A `null` value means no per-hour ceiling is enforced for that tenant. For Basic and Standard tenants, the ceiling is a hard limit enforced by the orchestrator. **[PROPOSED — queue-not-reject behavior: the vault sources this pattern only for cost cap exhaustion (source: [[analyses/llm-operational-safeguards]] §Cost Control); whether hourly rate-limit exhaustion queues or rejects pipeline runs is not specified. Recommend queuing for consistency with cost-cap behavior, but this is a team decision.]**

---

### Group 2 — LLM Cost Controls

These fields control per-tenant LLM spend. The enforcement mechanism (alert at 80%, hard stop at 100%, midnight UTC reset) is defined in [[analyses/llm-operational-safeguards]] §Cost Control and applies uniformly regardless of these field values.

| Field | Type | Basic | Standard | Premium | Overridable By | Override Bounds |
|-------|------|-------|----------|---------|----------------|-----------------|
| `daily_llm_cost_cap_usd` | decimal | 5.00 | `[TBD]` | `[TBD]` | Tenant admin (lower only) **[PROPOSED]** | Cannot be raised above tier default; can be lowered. **[PROPOSED — no minimum floor specified in vault; directional constraint is a design choice]** |

**Only Basic is defined in the vault:** The $5.00 Basic daily cap is documented in [[analyses/llm-operational-safeguards]] §Cost Control. Standard and Premium values are not set in existing documentation and must be established by the team. These depend on expected lead volume per tier and Anthropic pricing.

**Override rule for `daily_llm_cost_cap_usd`:** **[PROPOSED design choice — not specified in vault]** A tenant admin can lower their own cap below the tier default (e.g., a Basic tenant wanting a stricter $2.00/day budget). A tenant admin cannot raise the cap above the tier default — that requires a platform admin action (or a tier upgrade). This is the **tenant-can-lower, platform-controls-ceiling** pattern. The vault only states the field is "configurable per tenant in `tenant_config`" (source: [[analyses/llm-operational-safeguards]] §Cost Control); it does not specify who can change it or in which direction. The override direction and role restriction proposed here are design decisions the team should confirm.

**Hard-stop behavior:** When a tenant reaches 100% of their daily cap, new scoring calls for that tenant are placed in a queue but not executed. Calls already in-flight complete. The queue drains automatically at midnight UTC. All other tenants are unaffected. (source: [[analyses/llm-operational-safeguards]] §Cost Control)

---

### Group 3 — Token Budget

These fields control the maximum number of tokens consumed per LLM call for this tenant.

| Field | Type | Basic | Standard | Premium | Overridable By | Override Bounds |
|-------|------|-------|----------|---------|----------------|-----------------|
| `token_budget_per_lead` | int \| null | 4,000 | 8,000 | `null` (unlimited; alert fires at 12,000) | Platform admin | Cannot exceed tier max; can be lowered. **[PROPOSED — no minimum floor specified in vault]** |

**`null` semantics for Premium:** A `null` budget does not mean unlimited tokens literally — the Sonnet 4.6 practical limit for reliable structured output is 16,000 tokens and is a hard block regardless of tier (returns `PromptTooLargeError`; routes lead to `human_review` with `reason = 'prompt_too_large'`). `null` means no platform-enforced per-tenant ceiling below the model's absolute limit.

**Truncation behavior:** When prompt assembly would exceed the budget, `touchpoints` (lowest-priority field, longest in character count) are truncated first. Required signal fields and the persona context are never truncated. (source: [[analyses/llm-operational-safeguards]] §Token Monitoring)

**Pre-call estimation:** The orchestrator estimates token count before the call using a tokenizer. If the estimate exceeds `token_budget_per_lead`, truncation occurs before the call — not after.

---

### Group 4 — API Rate Limits

These fields control how many requests per minute a tenant can make to the **Reporting Service REST API**. They do not apply to the ingestion service or pipeline webhook endpoints.

| Field | Type | Basic | Standard | Premium | Overridable By | Override Bounds |
|-------|------|-------|----------|---------|----------------|-----------------|
| `api_requests_per_minute` | int | 30 | 100 | 500 | Platform admin | Cannot exceed tier max; can be lowered |

**Enforcement point:** The Reporting Service returns a `429 Too Many Requests` response when the limit is exceeded; the client is responsible for backing off. **[PROPOSED — the enforcement architecture (API gateway layer vs application code) is not specified in the vault. The tiering table in [[analyses/service-scaling-strategy]] names "API requests per minute (reporting)" as a tier dimension but does not describe the enforcement mechanism.]**

---

### Group 5 — Reporting Configuration

These fields control what scheduled reporting a tenant receives. The schedule type is **tier-locked** — it cannot be overridden, only upgraded by changing tier.

| Field | Type | Basic | Standard | Premium | Overridable By | Notes |
|-------|------|-------|----------|---------|----------------|-------|
| `scheduled_reports` | enum: `none \| weekly_digest \| daily_digest \| custom` | `none` | `weekly_digest` | `daily_digest` + `custom` allowed | **Tier-locked. No override.** | Upgrading report schedule requires a tier upgrade. |

**`custom` schedule:** Only Premium tenants can define a custom report schedule (e.g., Monday + Thursday, or on-demand trigger). The `report_definition` entity (Group C of the 32-entity catalog) stores the definition. At MVP, `custom` is defined in schema but not implemented — only `weekly_digest` and `daily_digest` are implemented.

**Pre-computation rule:** All scheduled reports are generated by a background job and stored as `report_artifact` records. No report is generated live on request. (source: [[analyses/service-scaling-strategy]] Recommendation 14; [[analyses/delivery-integration-layer]])

**Report delivery endpoint:** Where scheduled reports are sent (email, in-app, webhook) is not defined in the existing documentation. This is a delivery configuration gap — the `delivery_endpoint` entity in the 32-entity catalog (Group C) is the intended storage location, but the specific fields for report routing are not yet specified.

---

### Group 6 — Quality Gate Settings

These fields control the completeness threshold that routes a lead to the human review queue.

| Field | Type | Basic | Standard | Premium | Overridable By | Override Bounds |
|-------|------|-------|----------|---------|----------------|-----------------|
| `needs_review_threshold` | float 0.0–1.0 | `[TBD]` | `[TBD]` | `[TBD]` | Team lead | Any value in 0.0–1.0; defaults apply until team decision |

**Why per-tenant:** Different tenants have fundamentally different lead data quality norms. A B2C WhatsApp-only tenant will structurally have lower lead completeness scores (less company data, less enrichment possible) than a B2B LinkedIn tenant. A single system-wide threshold would produce inappropriate review routing rates for tenants at opposite ends of this spectrum.

**Source ambiguity — read before building:** [[analyses/rating-agent-spec]] §Completeness Output shows a routing table with three fixed bands: ≥80% (auto-assign), 50–79% (WARNING flag), <50% (needs_review = true). However, the same document separately states "Threshold for needs_review: [TBD — S2 suggests 0.6 or 0.75 as starting options; team decision]" — a configurable threshold that would be *higher* than the fixed 50% floor in the routing table. These two values are not reconciled in the source. Interpretation: the fixed 50% is a hard floor (leads below 50% completeness always get needs_review); the `needs_review_threshold` is an additional configurable trigger for the range between the floor and 79%. The team must resolve this before build. If the threshold is 0.75, leads with completeness between 50% and 75% will also be flagged.

**Override role:** Team lead (not salesperson, not viewer). **[PROPOSED — see Role Permissions table note in §Part 4]** The team lead is the role responsible for scoring quality in their tenant. Changing this threshold affects how many leads land in the human review queue.

---

### Group 7 — Infrastructure Settings

These fields control the infrastructure model for this tenant. They are **tier-locked** and can only be changed by a platform admin.

| Field | Type | Basic | Standard | Premium | Overridable By | Notes |
|-------|------|-------|----------|---------|----------------|-------|
| `infra_model` | enum: `pool \| silo` | `pool` | `pool` | `pool` (silo by explicit request) | Platform admin only | Silo requires physical migration; not a config toggle |
| `read_path` | enum: `shared_replica \| dedicated_replica` | `shared_replica` | `shared_replica` | `dedicated_replica` | Platform admin only | Dedicated replica provisioned per tenant |

**MVP note:** All three POC tenants (Gamoft, Urvee Organics, Govmen) are `pool` + `shared_replica`. The `silo` and `dedicated_replica` values are defined in the schema but are not operative at MVP. Activating `silo` for a Premium tenant requires an explicit platform migration — setting `infra_model = silo` in the config record is not sufficient; it is a flag that marks the tenant as eligible for silo migration, triggering a provisioning workflow.

---

### Group 8 — LLM Model and Prompt Version Configuration

These fields control which LLM model and prompt version are used for this tenant's scoring calls.

| Field | Type | Default | Overridable By | Notes |
|-------|------|---------|----------------|-------|
| `llm_model_override` | string \| null | `null` (use system default) | Platform admin | See Open Decision 2 below |
| `active_prompt_version` | string \| null | `null` (always use latest active version from `prompt_registry`) | Platform admin | See Open Decision 3 below |

**`llm_model_override` null semantics:** `null` means this tenant uses whatever `system_config.default_llm_model` specifies (currently `claude-sonnet-4-6`). A non-null value locks this tenant to a specific model, independent of the system default. (source: [[analyses/rating-agent-spec]] Open Decisions — model config scope TBD)

**`active_prompt_version` null semantics:** `null` means this tenant always receives the latest published version from `prompt_registry`. A pinned version string locks this tenant to a specific prompt version — useful when a tenant's scoring behavior has been calibrated against a known prompt version and the team wants to avoid automatic updates.

---

## Part 3 — Tier Defaults Matrix

Complete reference for all `tenant_config` field defaults across all tiers. (Sources: [[analyses/service-scaling-strategy]] §Tiering; [[analyses/llm-operational-safeguards]] §Token Monitoring, §Cost Control)

| Field | Basic (MVP default) | Standard | Premium |
|-------|---------------------|----------|---------|
| `scoring_concurrency_cap` | 2 | 3 | 5 |
| `pipeline_runs_per_hour` | 20 | 50 | null (unlimited) |
| `token_budget_per_lead` | 4,000 | 8,000 | null (alert at 12,000) |
| `daily_llm_cost_cap_usd` | 5.00 | `[TBD]` | `[TBD]` |
| `api_requests_per_minute` | 30 | 100 | 500 |
| `scheduled_reports` | none | weekly_digest | daily_digest + custom |
| `needs_review_threshold` | `[TBD after Month 1]` | `[TBD]` | `[TBD]` |
| `infra_model` | pool | pool | pool (silo by request) |
| `read_path` | shared_replica | shared_replica | dedicated_replica |
| `llm_model_override` | null | null | null |
| `active_prompt_version` | null | null | null |

**All three POC tenants at launch:** Basic tier across all fields.

---

## Part 4 — Override Rules and Enforcement

### Resolution Order

When the orchestrator loads `tenant_config`, the effective value for each field is read directly from the `tenant_config` record. There is no runtime tier-lookup or default-fallback at load time — the effective values are pre-computed and stored.

```
Tier change or tenant activation
        │
        ▼
Platform populates tenant_config from tier defaults
        │
        ▼ (optional — authorized role applies override)
Override applied if within bounds → stored in tenant_config
        │
        ▼
Orchestrator reads tenant_config at P1-0d
        │
        ▼ effective value applied throughout pipeline run
```

This means: changing a tier default does **not** retroactively change existing `tenant_config` records. A tier upgrade populates the new tier's defaults only for fields that have no tenant-specific override. Fields with existing overrides are preserved if within the new tier's bounds; discarded if not.

---

### Role Permissions for Overrides

> **[PROPOSED — per-field assignments not in vault]:** The 4-role RBAC model (platform admin, tenant admin, team lead, salesperson/viewer) is established in [[analyses/governance-observability-layer]] §Security. However, **all per-field cell assignments in the table below are derived from role responsibility descriptions — they are not explicitly specified in any vault document.** This table is a reasoned design proposal; the team should review and confirm each assignment before build.

| Field | Platform Admin | Tenant Admin | Team Lead | Salesperson | Viewer |
|-------|----------------|-------------|-----------|-------------|--------|
| `tenant.tier` | ✓ change | — | — | — | — |
| `scoring_concurrency_cap` | ✓ override | — | — | — | — |
| `pipeline_runs_per_hour` | ✓ override | — | — | — | — |
| `token_budget_per_lead` | ✓ override | — | — | — | — |
| `daily_llm_cost_cap_usd` | ✓ override (any value within tier) | ✓ lower only (cannot raise above tier default) | — | — | — |
| `api_requests_per_minute` | ✓ override | — | — | — | — |
| `scheduled_reports` | ✓ (tier change only) | — | — | — | — |
| `needs_review_threshold` | ✓ override | — | ✓ override (0.0–1.0 range) | — | — |
| `infra_model` | ✓ (triggers migration workflow) | — | — | — | — |
| `read_path` | ✓ (triggers provisioning) | — | — | — | — |
| `llm_model_override` | ✓ override | — | — | — | — |
| `active_prompt_version` | ✓ override | — | — | — | — |

**Role definitions:** platform admin = Gamoft employee with full system access; tenant admin = the client org's admin user (created at onboarding Stage 1, automatically assigned `tenant_admin` RBAC role); team lead and salesperson = tenant users with their respective RBAC roles.

---

### Override Bounds and Rejection Behavior

When an override request would exceed the tier's maximum:
- The request is **rejected** with an explicit error — it is not silently capped at the tier maximum.
- Error message must state the tier maximum and suggest a tier upgrade if needed.
- The existing `tenant_config` value is unchanged.

**[PROPOSED design principle] Rationale for rejection over silent cap:** Silent capping creates a class of invisible overrides where the configured value differs from the effective value, breaking the admin's mental model. Explicit rejection keeps the schema honest. This enforcement choice is not specified in the vault — it is a design recommendation.

---

### When Changes Take Effect

| Change type | Takes effect | Cache behavior |
|-------------|-------------|----------------|
| `tenant_config` field update | Next pipeline run started after the write | `tenant_config` is loaded fresh at each P1-0d context load — it is not cached with a TTL the way the PersonaObject is |
| `tenant.tier` change | After `tenant_config` is re-populated (synchronous on tier change) | Same as above |
| `llm_model_override` or `active_prompt_version` update | Next pipeline run | PersonaObject cache (15-min TTL) is separate; prompt changes do not invalidate the PersonaObject cache |
| `needs_review_threshold` update | Next scoring call | Loaded as part of `tenant_config`; no separate cache |

**Important distinction:** The PersonaObject (scoring weights, banding, ICP definition) has a 15-minute TTL in the Persona Engine cache (source: [[analyses/rating-agent-spec]] Component 1). The `tenant_config` is NOT cached with a TTL — it is loaded fresh on each pipeline run's context load. This means operational limit changes (like a concurrency cap update) take effect at the next run without waiting for a cache to expire.

---

## Part 5 — `system_config` Settings

`system_config` is a **new entity** not in the 32-entity catalog. It holds platform-wide operational settings that apply to all tenants uniformly. There is one `system_config` record for the entire platform (singleton).

| Field | Type | MVP Default | Mutable By |
|-------|------|-------------|-----------|
| `system_monthly_cost_cap_usd` | decimal | 100.00 | Platform admin |
| `cost_alert_threshold_pct` | float 0.0–1.0 | 0.80 | **[PROPOSED configurable]** — documented as a constant (80%) in source, not a configurable setting; see note below |
| `default_tier` | enum: `basic \| standard \| premium` | `basic` | Platform admin |
| `default_llm_model` | string | `claude-sonnet-4-6` | Platform admin |
| `cost_anomaly_multiplier` | float | 3.0 (3× rolling 7-day per-tenant average) | **[PROPOSED configurable]** — documented as a constant (3×) in source, not a configurable setting; see note below |
| `persona_cache_ttl_seconds` | int | 900 (15 minutes) | **[PROPOSED configurable]** — documented as a constant (15 min) in source, not a configurable setting; see note below |
| `max_prompt_tokens` | int | 16,000 (Sonnet 4.6 practical structured-output limit; returns `PromptTooLargeError` if exceeded) | Not configurable |

**[PROPOSED configurable] note:** Three fields in this table are documented as **constants** in vault sources — not as configurable settings:
- `cost_alert_threshold_pct` (80%) — documented as a fixed constant in [[analyses/llm-operational-safeguards]] §Cost Control, not as a configurable parameter.
- `cost_anomaly_multiplier` (3×) — documented as a fixed constant in [[analyses/llm-operational-safeguards]] §Cost Control.
- `persona_cache_ttl_seconds` (900s / 15 min) — documented as a fixed constant in [[analyses/rating-agent-spec]] Component 1.

Placing these in `system_config` with "Platform admin" mutability is a **design proposal** — it makes operational sense (admins may need to tune these over time) but it is not specified in the vault. The team should decide at build time whether these are runtime-configurable or hardcoded constants alongside the LLM call timeouts.

**Hardcoded timeouts (not in `system_config`):** The LLM call timeouts (30s attempt 1, 45s attempt 2, 60s full `score_lead()`, 90s end-to-end pipeline) are implementation constants in the application code, not configurable at runtime. (source: [[analyses/llm-operational-safeguards]] §RETRY_STRATEGY; [[analyses/rating-agent-spec]] §Timeouts)

**System monthly cap behavior:** When the platform reaches 100% of `system_monthly_cost_cap_usd`, all new scoring calls across all tenants are hard-stopped. Only a platform admin can lift the cap or wait for the calendar month to roll over. (source: [[analyses/llm-operational-safeguards]] §Cost Control)

---

### `provider_pricing_config` (Separate Entity — Required)

`provider_pricing_config` is a **new entity** required by the cost calculation formula. Pricing must not be hardcoded in application code because provider pricing changes over time. (source: [[analyses/llm-operational-safeguards]] §Cost Control)

| Field | Type | Notes |
|-------|------|-------|
| `provider` | string | e.g., `anthropic`, `openai` |
| `model` | string | e.g., `claude-sonnet-4-6`, `gpt-4o` |
| `input_token_price_usd` | decimal | Cost per input token |
| `cached_input_token_price_usd` | decimal | Cost per cached input token (Anthropic: 90% less than `input_token_price_usd`) |
| `output_token_price_usd` | decimal | Cost per output token |
| `effective_from` | timestamp | When this pricing row becomes active |
| `effective_to` | timestamp \| null | `null` = currently active pricing |

**Storage decision (open):** The llm-operational-safeguards doc flags this as an unresolved team decision: DB table vs config file vs env var. DB table is the most flexible (allows runtime price updates without deployment); env var is the simplest for MVP. This document defines the schema either way; the storage decision determines the implementation.

---

## Part 6 — Entity Gaps

The four entities introduced or surfaced by this document are not in the 32-entity catalog from [[sources/2026-core-business-entities]]:

| Entity | Gap type | Required for |
|--------|----------|--------------|
| `tenant_config` | Missing from catalog | Operational limits; loaded at P1-0d; the main subject of this document |
| `system_config` | Missing from catalog | System-wide cost caps, default tier, default model |
| `provider_pricing_config` | Missing from catalog | LLM cost calculation; flagged as a required addition in [[analyses/llm-operational-safeguards]] |
| `prompt_registry` | Missing from catalog | Stores versioned prompt templates per tenant; referenced in [[analyses/rating-agent-spec]] (inputs table), [[analyses/execution-type-classification]] (P2-3 output), [[analyses/onboarding-flow-readiness]] (Condition 1), [[analyses/orchestration-layer-spec]] (§P2 Pipeline Controller, §6.1 step 7), [[analyses/persona-agent-spec]] §Step 3, [[analyses/governance-observability-layer]]; loaded at Pipeline 1 pre-flight alongside `tenant_config` and persona |

Additionally, the `tenant` entity in the catalog needs one field added: **`tier`** (enum: `basic | standard | premium`). The existing `tenant` entity definition does not include this field.

These five changes should be applied to the entity catalog before the build phase begins.

---

## Evidence

- Tier defaults matrix (concurrency caps 2/3/5, pipeline runs/hour 20/50/unlimited, token budgets 4K/8K/unlimited, API rate limits 30/100/500, scheduled reports none/weekly/daily+custom, read path shared/shared/dedicated): (source: [[analyses/service-scaling-strategy]] §Tiering)
- Per-tenant daily LLM cost cap $5.00 for Basic, stored in `tenant_config`; system monthly cap $100.00 in `system_config`; 80% alert / 100% hard stop; midnight UTC reset; queue-not-reject behavior: (source: [[analyses/llm-operational-safeguards]] §Cost Control)
- Token budget by tier (4K/8K/unlimited with 12K alert): (source: [[analyses/llm-operational-safeguards]] §Token Monitoring)
- `PromptTooLargeError` at 16,000 tokens; `touchpoints` truncation before signal fields: (source: [[analyses/llm-operational-safeguards]] §Token Monitoring)
- Concurrency cap as semaphore keyed on `tenant_id`; recommended starting value 2 per tenant; tunable via `tenant_config`: (source: [[analyses/service-scaling-strategy]] Recommendation 6; [[analyses/rating-agent-spec]] §Per-Tenant Concurrency Cap)
- `tenant_config` loaded at P1-0d Context Loading alongside `persona` and `signal_definitions` as separate DB reads: (source: [[analyses/execution-type-classification]] P1-0d)
- `tenant_config` referenced as the surface for bucket threshold updates and signal weight updates (stored separately from `tenant_config` in `signal_definitions`): (source: [[analyses/orchestration-layer-spec]] §Config Change Pathway)
- PersonaObject cache TTL 15 minutes: (source: [[analyses/rating-agent-spec]] Component 1 — Persona Engine)
- `provider_pricing_config` identified as a required missing entity: (source: [[analyses/llm-operational-safeguards]] §Cost Control — "pricing must be read from a config table, not hardcoded")
- Pre-computation rule for reports; `report_job` and `report_artifact` as S1 delivery entities: (source: [[analyses/service-scaling-strategy]] Recommendation 14; [[analyses/delivery-integration-layer]])
- RBAC 4-role model (admin, team_lead, salesperson, viewer): (source: [[analyses/governance-observability-layer]] §Security)
- `needs_review` completeness routing bands and TBD threshold value: (source: [[analyses/rating-agent-spec]] §Completeness Output)
- `infra_model = pool` as MVP architecture for all tenants; bridge model for future: (source: [[analyses/service-scaling-strategy]] §Pool Model, §Bridge Model)

---

## Caveats & Gaps

1. **Standard and Premium daily LLM cost caps not defined.** Only the Basic $5.00 value is in the vault. Standard and Premium default `daily_llm_cost_cap_usd` values must be set before those tiers are activated. Suggest setting after Month 1 when per-tenant LLM cost data is available.

2. **`needs_review_threshold` default value is TBD.** Explicitly deferred to team decision after Month 1 baseline data. Until a value is set, the system cannot enforce the completeness gate correctly. A temporary hardcoded default (0.60 or 0.75) may be needed to unblock build. See Open Decision 1.

3. **Haiku (Message Parser) concurrency cap scope not specified.** The `scoring_concurrency_cap` is documented for the Sonnet Rating Agent call. Whether the Haiku Message Parser call (DM path only) is governed by the same semaphore or a separate limit is unresolved. Recommending: share the same semaphore at MVP for simplicity; add a separate cap if Haiku call volume causes measurable throttling.

4. **Report delivery endpoint configuration not defined.** The `delivery_endpoint` entity exists in the 32-entity catalog (Group C) but the specific fields for configuring report delivery routing (email address, webhook URL, in-app only) are not yet specified. This is a gap in the delivery layer, not this document's scope to resolve.

5. **`custom` scheduled reports not implemented at MVP.** The enum value is defined; the implementation is deferred. Premium tenants will see the option in the schema but it will return a "not yet available" response until implemented.

6. **`infra_model = silo` not a simple toggle.** Setting `infra_model = silo` in `tenant_config` is a flag that marks a tenant as eligible for silo migration, not an immediate config change. A physical provisioning workflow must run. The exact steps for silo provisioning are not defined.

7. **Per-tenant model override is an open team decision.** Whether different tenants can use different LLM models is unresolved (source: [[analyses/rating-agent-spec]] Open Decisions). The `llm_model_override` field is defined in this schema to support both paths; if the team decides against per-tenant overrides, the field remains permanently `null`.

8. **`tenant_config` is not cached with a TTL.** This means every pipeline run performs a DB read for `tenant_config`. At ~300 leads/day this is negligible. If volume grows significantly, a short TTL cache (1–5 minutes) may be warranted. Flagged for future consideration.

---

## Open Decisions

| Decision | Options | Where Documented | Impact |
|----------|---------|-----------------|--------|
| `needs_review_threshold` default | 0.60 (lenient — fewer reviews) or 0.75 (conservative — more reviews) | [[analyses/rating-agent-spec]] Open Decisions | Determines human review queue volume from day 1 |
| `daily_llm_cost_cap_usd` for Standard/Premium | Team to set after Month 1 cost data | This document, §Group 2 | Cannot activate Standard/Premium tier without these values |
| Per-tenant `llm_model_override` scope | Global default only vs per-tenant override allowed | [[analyses/rating-agent-spec]] Open Decisions | Determines whether the `llm_model_override` field ever gets a non-null value |
| `active_prompt_version` pinning | Always-latest vs per-tenant version lock | [[analyses/rating-agent-spec]] Open Decisions — prompt storage in code vs data layer | Affects how prompt updates are deployed; version-pinned tenants are protected from accidental prompt regressions |
| `provider_pricing_config` storage | DB table (runtime-updatable) vs config file in repo (deploy-to-change) vs env var (simplest) | [[analyses/llm-operational-safeguards]] Open Decisions | Determines operational procedure when provider pricing changes |
| Starting `scoring_concurrency_cap` value | 2 per tenant recommended; depends on Anthropic account rate limits | [[analyses/rating-agent-spec]] Open Decisions | Final value depends on Anthropic account rate limits obtained during onboarding |

---

## Follow-up Questions

- Should `daily_llm_cost_cap_usd` be expressed in USD only, or should the system support other currencies for non-USD tenants? Currently USD throughout. If multi-currency support is ever needed, the cost calculation formula will need a currency conversion layer.
- Should `pipeline_runs_per_hour` be a rolling-window rate limit (last 60 minutes) or a fixed-window (resets on the hour)? The tiering table in service-scaling-strategy does not specify. Rolling window is fairer to tenants; fixed window is simpler to implement.
- Should the team lead be able to view `tenant_config` fields in a read-only dashboard, even if they cannot modify most of them? Visibility into current limits would help team leads understand why leads are being queued.
- At what tenant count / lead volume does `tenant_config` caching become worth implementing?

---

## Related Documents

- [[analyses/client-config-schema-business-profile]] — Subtask 1: business profile fields (Group 1–4)
- [[analyses/client-config-schema-persona-scoring]] — Subtask 2: scoring weights, banding, signal weights, tone, custom rules
- [[analyses/service-scaling-strategy]] — tiering framework and noisy-neighbor analysis; source for all tier defaults
- [[analyses/llm-operational-safeguards]] — retry strategy, fallback strategy, cost caps, token budgets; source for LLM cost fields
- [[analyses/rating-agent-spec]] — concurrency cap, timeout values, `needs_review_threshold` TBD; open model/prompt decisions
- [[analyses/execution-type-classification]] — P1-0d Context Loading (where `tenant_config` is fetched)
- [[analyses/governance-observability-layer]] — RBAC role definitions; security model
- [[sources/2026-core-business-entities]] — authoritative entity catalog (gaps in §Entity Gaps must be added here)
- [[analyses/onboarding-flow-readiness]] — `tenant.status` state machine; activation effects
