# Pipeline I/O Contracts — Lead Intelligence Engine

**Epic:** 0.3 — End-to-End Workflow Decomposition  
**JIRA AC:** "I/O contract sheet completed for all workflow steps"  
**Date:** 2026-05-20  
**Status:** APPROVED planning artifact — satisfies Epic 0.3 AC  
**Sources:** `wiki/analyses/orchestration-layer-spec.md`, `wiki/analyses/llm-io-contract.md` v1.1.0, `wiki/analyses/global-data-collection-architecture.md`, `wiki/analyses/context-construction-specification.md`

---

## How to Read This Document

Each step has:

- **Path** — which leads go through this step: `DM` (WhatsApp/IG/FB DM), `LEAD_AD` (Facebook/Instagram Lead Ads), or `BOTH`
- **pipeline_stage** — the `leads.pipeline_stage` value before and after this step (locked enum — see `orchestration-layer-spec.md` §8.1)
- **Input** — typed fields the step receives. `?` = optional/nullable. `enum(...)` = locked value set.
- **Output** — typed fields the step produces. All output fields are written to the `leads` table or lineage unless marked otherwise.
- **On Failure** — what the orchestrator does if the step errors or times out.

All field names are canonical and match the DB column names. Any deviation is a bug.

---

## Pipeline 2 — Tenant Onboarding (runs once per tenant)

Pipeline 2 runs at tenant setup and whenever the business profile changes significantly. All steps are sequential. Team lead approves before re-runs.

---

### P2-S1 — Onboarding Agent (LLM: Claude Sonnet)

| | |
|---|---|
| **Path** | Onboarding only |
| **Execution type** | AGENT (LLM) |
| **pipeline_stage before** | `onboarding_started` |
| **pipeline_stage after** | `persona_generated` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `tenant_description` | `string` (min 50 chars) | Yes | Free-text business description collected in Onboarding Stage 3 |
| `business_type_hint` | `enum("B2B", "B2C", "hybrid") \| null` | No | Pre-classification from form fields; LLM may override |
| `prior_persona` | `PersonaObject \| null` | No | Present on re-runs only; null on first onboarding |
| `tenant_id` | `uuid` | Yes | |
| `persona_version_prior` | `semver \| null` | No | Version of prior persona being replaced |

**Output — PersonaObject (partial, passed to P2-S2)**

| Field | Type | Description |
|---|---|---|
| `tenant_name` | `string` | Canonical business name |
| `business_type` | `enum("B2B", "B2C")` | Resolved mode; drives all downstream behaviour |
| `business_summary` | `string` (max 500 chars) | Concise description for LLM system prompt injection |
| `target_markets` | `string[]` | Primary markets served |
| `key_value_props` | `string[]` | Top 3–5 value propositions |
| `icp_notes` | `string` | Raw narrative for ICP Agent input |

**On Failure:** 1 retry → if still fails → halt onboarding, alert admin, do not proceed to P2-S2.

---

### P2-S2 — ICP Agent (LLM: Claude Sonnet)

| | |
|---|---|
| **Path** | Onboarding only |
| **Execution type** | AGENT (LLM) |
| **pipeline_stage before** | `persona_generated` |
| **pipeline_stage after** | `icp_generated` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `persona_partial` | `PersonaObject` | Yes | Output of P2-S1 |
| `tenant_description` | `string` | Yes | Same raw input as P2-S1 |
| `tenant_id` | `uuid` | Yes | |

**Output — IcpDefinition**

| Field | Type | Description |
|---|---|---|
| `ideal_customer_description` | `string` (max 1000 chars) | Narrative injected into scoring system prompt |
| `company_size_range` | `string \| null` | e.g. `"20–500 employees"` (B2B only) |
| `target_industries` | `string[]` | e.g. `["SaaS", "FinTech"]` (B2B only) |
| `target_roles` | `string[]` | Decision-maker titles (B2B only) |
| `geographic_focus` | `string[]` | e.g. `["India Tier 1", "India Tier 2"]` |
| `disqualifying_profiles` | `string[]` | min 1 item; injected into scoring prompt |
| `b2c_buyer_profile` | `string \| null` | Description of ideal individual buyer (B2C only) |

**Storage:** `ideal_customer_profile` table (versioned in `ideal_customer_profile_version`).

**On Failure:** 1 retry → if still fails → halt onboarding, alert admin, do not proceed to P2-S3.

---

### P2-S3 — Signal Agent (LLM: Claude Sonnet)

| | |
|---|---|
| **Path** | Onboarding only |
| **Execution type** | AGENT (LLM) |
| **pipeline_stage before** | `icp_generated` |
| **pipeline_stage after** | `signals_generated` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `persona` | `PersonaObject` | Yes | Output of P2-S1 |
| `icp` | `IcpDefinition` | Yes | Output of P2-S2 |
| `dimensions_to_cover` | `string[]` | Yes | Always: `["fit","intent","engagement","behaviour","context"]` |
| `tenant_id` | `uuid` | Yes | |

**Output — signal[] (one record per scoring question)**

| Field | Type | Description |
|---|---|---|
| `signal_id` | `uuid` | Generated |
| `dimension` | `enum("fit","intent","engagement","behaviour","context")` | |
| `name` | `string` (snake_case) | e.g. `pricing_request` |
| `description` | `string` | Human-readable definition of what to detect |
| `detection_rule` | `{type: string, source_fields: string[], params: object}` | Named extractor + params; see `signal-detection-rule-spec.md` |
| `weight_within_dim` | `float` (0.0–1.0; all weights within a dimension must sum to 1.0) | |
| `applicable_to` | `enum("B2B","B2C","both")` | |

**Storage:** `signal` table (S1). Minimum: 3 signals per dimension.

**On Failure:** 1 retry → if still fails → halt onboarding, alert admin, do not proceed to P2-S4.

---

### P2-S4 — Prompt Template Builder (deterministic)

| | |
|---|---|
| **Path** | Onboarding only |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `signals_generated` |
| **pipeline_stage after** | `prompt_built` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `persona` | `PersonaObject` | Yes | Complete PersonaObject from P2-S1 |
| `icp` | `IcpDefinition` | Yes | From P2-S2 |
| `signals` | `signal[]` | Yes | All signals from P2-S3 |
| `tenant_id` | `uuid` | Yes | |

**Output**

| Field | Type | Description |
|---|---|---|
| `prompt_id` | `uuid` | |
| `prompt_version` | `semver` | e.g. `v1.0.0` |
| `system_message` | `string` | Static portion: role + ICP + signal weights + output format |
| `user_message_template` | `string` | Template with named slots `{signal_name}` for per-lead fill-in |
| `signal_slot_names` | `string[]` | Ordered list of all signal slots in the template |

**Storage:** `prompt_registry` table.

**On Failure:** Deterministic — must not fail. If it does, log and alert admin; root cause is always bad input from P2-S3.

---

### P2-S5 — ConfigSet Publication (deterministic)

| | |
|---|---|
| **Path** | Onboarding only |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `prompt_built` |
| **pipeline_stage after** | `onboarding_complete` → triggers `tenant.status = active` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `persona` | `PersonaObject` | Yes | |
| `icp` | `IcpDefinition` | Yes | |
| `signals` | `signal[]` | Yes | |
| `prompt_id` | `uuid` | Yes | From P2-S4 |
| `prompt_version` | `semver` | Yes | From P2-S4 |
| `tenant_id` | `uuid` | Yes | |

**Output**

| Field | Type | Description |
|---|---|---|
| `config_set_id` | `uuid` | |
| `config_version` | `semver` | |
| `published_at` | `datetime` (ISO 8601 UTC) | |
| `active` | `bool` | Always `true` on publish; prior version set to `false` |

**Side effect:** Scoring Agent picks up new ConfigSet on next cache refresh (15-minute TTL). `tenant.status` transitions to `active`. Onboarding Service receives `ClientOnboarded` event.

**On Failure:** Deterministic — must not fail. If it does, tenant stays in `onboarding` state; admin is alerted.

---

## Pipeline 1 — Lead Processing (runs per lead event)

Pipeline 1 runs per inbound lead. DM events (WhatsApp, Instagram DM, Facebook DM) traverse the full pipeline including Steps S1–S3. Lead Ad events (Facebook Lead Ads, Instagram Lead Ads) skip Steps S1–S3 and enter at S4 with structured form data already parsed.

---

### P1-S1 — Data Gather

| | |
|---|---|
| **Path** | BOTH |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | _(none — lead does not exist yet)_ |
| **pipeline_stage after** | `captured` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `tenant_id` | `uuid` | Yes | |
| `trigger_type` | `enum("scheduled","webhook","chat_request")` | Yes | |
| `channel_configs` | `ChannelConfig[]` | Yes | Per-channel credentials and endpoint config |
| `run_id` | `uuid` | Yes | Generated by orchestrator at run start |

**Output — NormalisedChannelEvent[] (one per raw inbound event)**

| Field | Type | Description |
|---|---|---|
| `event_id` | `uuid` | |
| `tenant_id` | `uuid` | |
| `channel` | `enum("whatsapp","instagram_dm","facebook_dm","lead_ad","website_form","linkedin")` | |
| `channel_thread_id` | `string` | Channel-native thread identifier (wa_id / igsid / psid / form_id) |
| `raw_payload` | `object` | Channel-specific raw webhook payload; immutable after this point |
| `received_at` | `datetime` (ISO 8601 UTC) | |
| `source` | `string` | Channel source label |

**Deduplication rule:** phone first → email second → name + location fallback. Duplicate events within the same run are discarded; the first is kept.

**On Failure (one channel):** Log, notify admin, continue with remaining channels.  
**On Failure (all channels):** Halt run, notify admin, set `pipeline_run.status = failed`.

---

### P1-S2 — Pre-Filter Gate _(DM path only)_

| | |
|---|---|
| **Path** | DM only |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `captured` |
| **pipeline_stage after** | `insufficient_signal` _(terminal, if filtered)_ or continues to P1-S3 |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `uuid` | Yes | |
| `raw_payload` | `object` | Yes | `NormalisedChannelEvent.raw_payload` |
| `channel` | `enum(...)` | Yes | |

**Output**

| Field | Type | Description |
|---|---|---|
| `proceed` | `bool` | `false` = message is noise/spam/no signal; pipeline terminates here |
| `discard_reason` | `string \| null` | Human-readable reason if `proceed = false` |
| `thread_context` | `{lead_id: uuid, prior_messages: string[]} \| null` | Populated if this message is a reply to an existing conversation thread |

**If `proceed = false`:** `pipeline_stage = insufficient_signal` (terminal). Lead record is created and stored for audit. No enrichment or scoring occurs. No enrichment API is called.

**On Failure:** Treat as `proceed = false`; log error; set `discard_reason = "pre_filter_error"`.

---

### P1-S3 — Message Parser _(DM path only)_ — LLM: Claude Haiku

| | |
|---|---|
| **Path** | DM only |
| **Execution type** | AGENT (LLM — Haiku) |
| **pipeline_stage before** | `captured` (continues from P1-S2) |
| **pipeline_stage after** | `fetched` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `message_text` | `string` | Yes | Raw message content |
| `thread_context` | `{prior_messages: string[]} \| null` | No | Present if this message is a thread reply (from P1-S2) |
| `channel` | `enum(...)` | Yes | |
| `tenant_id` | `uuid` | Yes | |

**Output**

| Field | Type | Description |
|---|---|---|
| `name` | `string \| null` | Extracted person name |
| `company` | `string \| null` | Extracted company name |
| `role` | `string \| null` | Extracted job title |
| `location_mentioned` | `string \| null` | City/region mentioned in message |
| `intent_text` | `string \| null` | Verbatim intent phrase from message |
| `business_ownership` | `bool` | `true` if message contains "I run a", "my company", "our firm" etc. |
| `language_detected` | `string` | ISO 639-1 code e.g. `"en"`, `"hi"` |
| `proceed` | `bool` | `false` = message has no extractable signal; maps to `insufficient_signal` terminal state |
| `discard_reason` | `string \| null` | Populated only if `proceed = false` |

**If `proceed = false`:** Same as P1-S2 — `pipeline_stage = insufficient_signal` (terminal).

**Retry policy:** max 2 attempts (1 original + 1 retry). On 2 consecutive failures: `pipeline_stage = failed`.

---

### P1-S4 — Lead Enrichment (includes Consent Gate and Signal Extraction)

| | |
|---|---|
| **Path** | BOTH (DM enters with Message Parser output; Lead Ad enters with structured form data) |
| **Execution type** | AUTOMATION (with external API calls) |
| **pipeline_stage before** | `fetched` |
| **pipeline_stage after** | `enriched` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `lead_id` | `uuid` | Yes | Created at P1-S1 |
| `tenant_id` | `uuid` | Yes | |
| `parsed_fields` | `ParsedLeadFields` | Yes | From Message Parser (DM) or structured Lead Ad form data |
| `channel` | `enum(...)` | Yes | |
| `signal_definitions` | `signal[]` | Yes | Loaded from tenant's active ConfigSet (P2-S3 output) |
| `feature_flags` | `object` | Yes | `tenant_config.feature_flags` — gates which enrichment providers are called |

**ParsedLeadFields sub-type**

| Field | Type | |
|---|---|---|
| `name` | `string \| null` | |
| `phone` | `string \| null` | Raw; normalised in P1-S5 |
| `email` | `string \| null` | |
| `company` | `string \| null` | |
| `role` | `string \| null` | |
| `location_mentioned` | `string \| null` | |
| `intent_text` | `string \| null` | |
| `business_ownership` | `bool` | |

**Embedded sub-steps (run in sequence inside this stage)**

| Sub-step | Cost | Gated by |
|---|---|---|
| Free Signal Scorer (B2B/B2C classification) | Zero | Always runs |
| Jurisdiction Classifier (country from phone prefix) | Zero | Always runs |
| Account Graph Check (prior company contact history) | DB lookup | Always runs |
| Company Cache Check | DB lookup | Always runs |
| Company Disambiguator | DB lookup + heuristics | Runs on cache miss |
| Company Resolver (API chain per jurisdiction) | External API | `feature_flags.enrichment_*` |
| Person Resolver (Truecaller, Apollo, etc.) | External API | `feature_flags.enrichment_*` |
| Location Reconciler (person city vs company HQ) | Heuristics | Always runs |
| Consent Gate (DPDP/GDPR jurisdiction check) | DB lookup | Always runs |
| Signal Extraction (deterministic, no LLM) | CPU | Always runs |

**Output — EnrichedLead**

| Field | Type | Description |
|---|---|---|
| `lead_id` | `uuid` | |
| `tenant_id` | `uuid` | |
| `name` | `string \| null` | |
| `phone` | `string \| null` | Raw E.164 (normalised in P1-S5) |
| `email` | `string \| null` | |
| `company_name` | `string \| null` | |
| `company_size_band` | `string \| null` | e.g. `"50–200"` |
| `company_revenue_band` | `string \| null` | |
| `industry` | `string \| null` | |
| `role` | `string \| null` | |
| `city` | `string \| null` | Person city (post-reconciliation) |
| `company_hq_city` | `string \| null` | Separate from person city |
| `country_code` | `string` | ISO 3166-1 alpha-2 |
| `city_tier` | `int \| null` | 1, 2, or 3 |
| `gstin` | `string \| null` | India B2B only |
| `cin` | `string \| null` | India B2B only |
| `business_type` | `enum("B2B","B2C")` | Resolved by Free Signal Scorer |
| `consent_status` | `enum("confirmed","inferred","not_required","blocked")` | From Consent Gate |
| `signal_values` | `SignalValues` | Keyed by dimension → signal name → typed value |
| `enrichment_providers_used` | `string[]` | Which providers contributed data |
| `enrichment_failures` | `{provider: string, reason: string}[]` | Providers that failed or were skipped |

**Consent Gate rule:** If `consent_status = "blocked"`, lead is scored on internal signals only; `enrichment_providers_used = []`.

**Feature flag enforcement:** Each external provider call is gated by its corresponding flag in `tenant_config.feature_flags`. Flag absent or `false` = skip provider, proceed to next in fallback chain.

**On Failure (one provider):** Skip provider, continue fallback chain. Log to `enrichment_failures`.  
**On Failure (all providers):** Mark lead with `enrichment_providers_used = []`, proceed to P1-S5 with partial data.

---

### P1-S5 — Normalise

| | |
|---|---|
| **Path** | BOTH |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `enriched` |
| **pipeline_stage after** | `normalised` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `enriched_lead` | `EnrichedLead` | Yes | Full output of P1-S4 |

**Output — NormalisedLead**

| Field | Type | Normalisation rule |
|---|---|---|
| `phone` | `string \| null` | E.164 format (`+{cc}{number}`) |
| `name` | `string \| null` | Title Case; emojis stripped; max 100 chars |
| `city` | `string \| null` | Canonical city name per jurisdiction lookup |
| `state` | `string \| null` | |
| `country_code` | `string` | ISO 3166-1 alpha-2 |
| `city_tier` | `int \| null` | 1 / 2 / 3 |
| `first_contact_date` | `string` | ISO 8601 UTC date |
| `lead_completeness` | `float` (0.0–1.0) | Fraction of expected signal fields present and non-null |
| `completeness_band` | `enum("complete","partial","sparse")` | complete ≥0.80 / partial 0.50–0.79 / sparse <0.50 |
| `all_signal_values` | `SignalValues` | All signals from tenant registry; missing signals set to `"not_detected"` — never null or absent |

**Conflict resolution:** most-recent data wins for contact details; CRM data overrides self-reported data. Unresolvable conflicts: store both values, flag for human review, log the conflict.

**Completeness calculation:** `(signals_with_non_null_value / total_signals_in_tenant_registry)`. The denominator is always the full registry count, not the signals that fired.

**On Failure:** Deterministic — must not fail. If it does, log the error; treat as `pipeline_stage = failed`.

---

### P1-S6 — Intent Gate

| | |
|---|---|
| **Path** | BOTH |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `normalised` |
| **pipeline_stage after** | `awaiting_clarification` (if paused) or continues to P1-S7 (if scoring proceeds) |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `normalised_lead` | `NormalisedLead` | Yes | |
| `intent_signals` | `SignalValues["intent"]` | Yes | Subset of signal values for the intent dimension |
| `fit_sub_score_estimate` | `float \| null` | No | Optional early fit estimate; used for the high-fit-low-intent gate |

**Output**

| Field | Type | Description |
|---|---|---|
| `action` | `enum("proceed_to_scoring","await_clarification")` | |
| `clarification_message` | `string \| null` | Populated only if `action = "await_clarification"`; sent to lead via originating channel |
| `clarification_channel` | `string \| null` | Channel on which to send the clarification prompt |
| `intent_penalty_applies` | `bool` | `true` if lead eventually scores after timeout with a penalty applied |

**Gate rule:** `await_clarification` fires when intent signals are very low AND fit estimate is high. The clarification message is sent via the originating channel. Pipeline pauses (`pipeline_stage = awaiting_clarification`).

**Resume rule:** Lead resumes at Normalise stage on reply. If no reply within 24 hours: lead scores with an intent penalty and transitions to `delivered`.

**On Failure:** Deterministic — treat as `action = "proceed_to_scoring"` and log.

---

### P1-S7 — Scoring Agent — LLM: Claude Sonnet

| | |
|---|---|
| **Path** | BOTH |
| **Execution type** | AGENT (LLM — Sonnet) |
| **pipeline_stage before** | `normalised` |
| **pipeline_stage after** | `scored` |

**Input — LLMInputContract (full typed schema: `wiki/analyses/llm-io-contract.md` §INPUT_SCHEMA)**

| Top-level field | Type | Description |
|---|---|---|
| `schema_version` | `string` (pattern `v\d+\.\d+`) | e.g. `"v1.1"` |
| `tenant_id` | `uuid` | |
| `lead_id` | `uuid` | |
| `variant` | `enum("new","returning","rescore")` | |
| `prompt_template_version` | `semver` | Active prompt version from `prompt_registry` |
| `lead` | `LeadObject` | Contact details: phone, channel, source, first_contact_date, name?, email?, geography?, city_tier? |
| `company` | `CompanyObject?` | Required for B2B: name, industry, size_employees, role, registration_id |
| `persona` | `PersonaObject` | Tenant configuration: icp_summary, disqualifying_profiles, scoring_weights, hot_min, warm_min, persona_version |
| `behavior` | `BehaviorObject` | revisit_count, channel_diversity, conversation_depth, follow_up_initiated, response_speed?, touchpoints[]? |
| `derived_metrics` | `DerivedMetrics` | lead_completeness (float), signal_values (by dimension) |
| `context_inputs` | `ContextInputs` | prior_score?, prior_bucket?, feedback_reason? (all null for `variant=new`) |

**Output — LLMOutputContract (full typed schema: `wiki/analyses/llm-io-contract.md` §OUTPUT_SCHEMA v1.1.0)**

| Field | Type | Description |
|---|---|---|
| `score` | `int` (0–100) | Overall lead score |
| `bucket` | `enum("hot","warm","cold")` | Raw LLM bucket; Output Schema Layer may override |
| `reasoning` | `ReasoningObject` | Structured: `primary_driver` (string), `signal_contributors` (array), `data_gaps` (string[]), `salesperson_note` (string) |
| `lead_completeness` | `float` (0.0–1.0) | Must echo input exactly; tolerance 0.001 |
| `sub_scores` | `{fit: int, intent: int, engagement: int, behaviour: int, context: int}` | Sub-scores must sum to `score` (tolerance ±1) |
| `recommended_action` | `enum("call_immediately","schedule_demo","send_pricing_deck","follow_up_scheduled","send_qualifying_message","nurture","archive")` | |
| `needs_review` | `bool` (always `false` from LLM) | Output Schema Layer overrides to `true` when `lead_completeness < threshold` |

**Post-LLM: Output Schema Layer adds three fields**

| Field | Source |
|---|---|
| `schema_version` | System constant from active ScoringOutput schema |
| `prompt_version` | `input.prompt_template_version` passed through |
| `model` | LLM provider API response metadata |

**Output Schema Layer also enforces:**
- `BUCKET_SCORE_CONSISTENCY` — if LLM bucket disagrees with score + tenant thresholds, threshold-derived bucket wins; discrepancy logged to `lineage_record`
- `NEEDS_REVIEW_GATE` — if `lead_completeness < configured threshold`, override `needs_review = true`, route to `human_review` queue

**Retry policy:** max 2 attempts. Retry appends schema correction message. On 2 consecutive failures: `pipeline_stage = human_review`, reason `scoring_failed`.

---

### P1-S8 — Bucketize

| | |
|---|---|
| **Path** | BOTH |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `scored` |
| **pipeline_stage after** | `scored` (bucket is set; stage advances at Deliver) |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `score` | `int` | Yes | From Scoring Agent |
| `bucket` | `enum("hot","warm","cold")` | Yes | From Output Schema Layer (already validated) |
| `lead_completeness` | `float` | Yes | |
| `needs_review` | `bool` | Yes | From Output Schema Layer |
| `tenant_banding` | `{hot_min: int, warm_min: int}` | Yes | From active ConfigSet |
| `disqualification_rules` | `DisqualRule[]` | Yes | Per-tenant; from ConfigSet. See DisqualRule schema below. |

**DisqualRule schema:**

```python
DisqualRule = TypedDict(
    condition_type: Literal[
        "serviceability_zero",   # lead.serviceability == 0
        "geography_mismatch",    # lead.geography not in tenant ICP geography_focus
        "role_mismatch",         # lead role matches disqualifying_profiles
        "spam_pattern",          # message classified as student/spam/irrelevant
    ],
    effect: Literal["score_cap", "score_delta", "force_zero"],
    value: int,          # cap floor for score_cap (e.g. 50); delta amount for score_delta (e.g. -30); 0 for force_zero
    reason_label: str,   # written to disqualification_reason field on the lead
)
```

Phase 1 generic rules (loaded for all tenants):
- `serviceability_zero` → `score_cap(50)`, reason: "Outside serviceable area"
- `geography_mismatch` → `score_delta(-30)`, reason: "Wrong geography"
- `role_mismatch` → `score_delta(-40)`, reason: "Non-decision-maker"
- `spam_pattern` → `force_zero(0)`, reason: "Student / spam / irrelevant"

Per-tenant custom rules defined at tenant onboarding via `disqualifying_signals` field in IcpDefinition.

**Disqualification Gate (runs before bucket assignment)**

| Condition | Effect |
|---|---|
| Outside serviceable area | Score capped at 50 or `disqualified` flag set |
| Wrong geography | −30 points applied to score |
| Non-decision-maker | −40 points applied to score |
| Student / spam / clearly irrelevant | Score forced to 0 |

**Output**

| Field | Type | Description |
|---|---|---|
| `bucket` | `enum("hot","warm","cold")` | Final bucket after disqualification adjustments |
| `sla_deadline` | `datetime` | HOT = now + 24h; WARM = now + 48h; COLD = now + 7d |
| `disqualification_applied` | `bool` | `true` if any disqualification rule fired |
| `disqualification_reason` | `string \| null` | |
| `routing` | `enum("deliver","human_review")` | `human_review` if `needs_review = true` or scoring failed |

**On Failure:** Deterministic — must not fail. If it does, log and route to `human_review`.

---

### P1-S9 — Deliver

| | |
|---|---|
| **Path** | BOTH |
| **Execution type** | AUTOMATION |
| **pipeline_stage before** | `scored` |
| **pipeline_stage after** | `delivered` or `human_review` |

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `lead_id` | `uuid` | Yes | |
| `tenant_id` | `uuid` | Yes | |
| `scoring_output` | `ScoringOutput` | Yes | Full output from P1-S7 + P1-S8 |
| `routing` | `enum("deliver","human_review")` | Yes | From P1-S8 |
| `salesperson_assignments` | `{user_id: uuid, role: string}[]` | Yes | RBAC-scoped per tenant |

**Output**

| Field | Type | Description |
|---|---|---|
| `delivery_id` | `uuid` | |
| `lead_card_created` | `bool` | Real-time lead card pushed to salesperson chat interface |
| `notification_sent` | `bool` | HOT leads trigger push notification via WebSocket service |
| `crm_synced` | `bool` | If CRM integration is active for this tenant |
| `webhook_fired` | `bool` | If external webhook is configured |
| `delivered_at` | `datetime` | ISO 8601 UTC |

**pipeline_stage write rule:** `delivered` is the final write. Written last, after all delivery channels confirm.

**On Failure (one delivery channel):** Log, continue with remaining channels. Never block `pipeline_stage = delivered` due to one channel failure.  
**On Failure (all delivery channels):** Route to `human_review`. Log all failures.

---

## Summary: pipeline_stage Transition Map

| Step | pipeline_stage → | Notes |
|---|---|---|
| P1-S1 Data Gather | _(none)_ → `captured` | Lead record created |
| P1-S2 Pre-Filter Gate | `captured` → `insufficient_signal` | **Terminal** — DM path only, no signal detected |
| P1-S3 Message Parser | `captured` → `fetched` | DM path; or `insufficient_signal` if proceed=false |
| P1-S4 Lead Enrichment | `fetched` → `enriched` | Lead Ad enters here directly |
| P1-S5 Normalise | `enriched` → `normalised` | |
| P1-S6 Intent Gate | `normalised` → `awaiting_clarification` | **Holding** — resumes on reply or after 24h |
| P1-S7 Scoring Agent | `normalised` → `scored` | Or `human_review` on scoring failure |
| P1-S8 Bucketize | `scored` → `scored` | Bucket set; stage unchanged |
| P1-S9 Deliver | `scored` → `delivered` or `human_review` | |
| Any step | any → `failed` | Retries exhausted |

**All accepted pipeline_stage values (locked):**  
`captured` · `fetched` · `enriched` · `normalised` · `scored` · `delivered` · `human_review` · `awaiting_clarification` · `insufficient_signal` · `failed`

---

## Write Order Rule (applies to every step)

```
Step 1 → Tool / LLM returns output
Step 2 → Orchestrator writes lineage entry (pipeline_run / task_execution / lineage_record)
Step 3 → Orchestrator writes output fields to leads table
Step 4 → Orchestrator updates pipeline_stage          ← ALWAYS LAST
```

`pipeline_stage` is the crash recovery checkpoint. If the system crashes between steps, it restarts from the current `pipeline_stage` on recovery.
