# Enrichment → LLM Field Map — Lead Intelligence Engine

**Epic:** 0.9 — Enrichment Integration  
**JIRA AC:** "Enrichment-to-LLM field map completed"  
**Date:** 2026-05-20  
**Status:** APPROVED planning artifact — satisfies Epic 0.9 AC  
**Sources:** `wiki/analyses/enrichment-tools-integration.md`, `wiki/analyses/llm-io-contract.md` v1.1.0, `wiki/analyses/pipeline-io-contracts.md`, `wiki/analyses/lead-enrichment-architecture.md`

---

## Purpose

This document traces the complete path from each enrichment provider's API response fields, through the intermediate `NormalisedEvent` / `EnrichedLead` context object, to the final LLM INPUT_SCHEMA fields consumed by the Scoring Agent at step P1-S7.

**Why this matters:** The Scoring Agent is blind to raw provider response format. It only sees the INPUT_SCHEMA. Without an explicit trace, a field missing from the mapping is silently absent from scoring — the LLM never sees it, can never use it.

---

## How to Read This Document

Each provider section shows:

1. **Provider output fields** — what the enrichment API returns, stored in `NormalisedEvent`
2. **Context object property** — the field name in `EnrichedLead` after the Normalise step (P1-S5)
3. **LLM INPUT_SCHEMA field** — the typed field in `llm-io-contract.md` INPUT_SCHEMA the Scoring Agent receives
4. **Signal(s) driven** — which signal values in `derived_metrics.signal_values` this field populates (if any)

**Signal evaluation is deterministic (not LLM).** Signal values are computed from `EnrichedLead` fields by the signal extraction layer before the Scoring Agent is called. The Scoring Agent receives pre-computed signal values — it does not compute them from raw enrichment data.

---

## Enrichment Providers

| Provider | Scope | Pipeline Phase |
|---|---|---|
| Truecaller | Phone identity — name, carrier, geography | P1-S4 Tier 1 (sync) |
| Google Places | Location, city tier | P1-S4 Tier 2 (sync) |
| Apollo.io | Company intelligence, email enrichment | P1-S4 Tier 2 (sync) |
| Surepass (GST/CIN/PAN) | Indian B2B government verification | P1-S4 Tier 2 (sync) |
| Probe42 | Indian SMB financials, legal records | P1-S4 Phase 2 (async) |
| Tracxn | Startup/funding stage intelligence | P1-S4 Phase 2 (async) |
| NewsCatcherAPI | Company news signals | P1-S4 Phase 2 (async) |
| IndiaMART / JustDial | B2B SMB directory presence | P1-S4 Phase 2 (async) |
| Serper.dev | Google Search fallback | P1-S4 Phase 2 (async, last resort) |

**Scope:** B2C = Truecaller + Google Places only (plus channel data). B2B India = all providers. B2B Global = Apollo + Tracxn + NewsCatcherAPI + Serper.

---

## 1. Truecaller

**Trigger:** All leads with a phone number. B2B and B2C.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_caller_name` | `str \| None` | `lead.name` | `lead.name` | — (used in salesperson note) |
| `enriched_carrier_name` | `str \| None` | `lead.carrier` | — (not in INPUT_SCHEMA) | — (stored; LLM connection and signal definition deferred to development time) |
| `enriched_carrier_country` | `str \| None` | `lead.geography` (country fallback) | `lead.geography` | `fit.serviceability` |
| `enriched_phone_type` | `str \| None` | `lead.phone_type` | — (not in INPUT_SCHEMA; used in pre-filter gate) | — |

**Note:** If `enriched_caller_name` is returned, it overwrites the name extracted by the Message Parser. Truecaller is the authoritative name source.

---

## 2. Google Places

**Trigger:** All leads where a location, city, or address can be extracted from the message or form fields.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_city` | `str \| None` | `lead.city` | `lead.geography` | `context.geography_tier` |
| `enriched_state` | `str \| None` | `lead.state` | `lead.geography` | `context.geography_tier` |
| `enriched_country` | `str \| None` | `lead.country` | `lead.geography` | `fit.serviceability` |
| `enriched_city_tier` | `int \| None` | `lead.city_tier` | `lead.city_tier` | `context.geography_tier` |
| `enriched_place_type` | `list[str] \| None` | `lead.place_type` | — (used to determine serviceability) | `fit.serviceability` (partial) |

**`lead.city_tier` mapping:**

| Google Places type | City tier |
|---|---|
| Tier 1 city (Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Pune, Kolkata) | `1` |
| Tier 2 city (Jaipur, Lucknow, Surat, Indore, etc.) | `2` |
| All other cities / towns / rural | `3` |
| Unknown (no geography resolved) | `null` |

**Signal computation:**

```
context.geography_tier = lead.city_tier
  → city_tier = 1  →  IntegerOrNotDetected value = 1
  → city_tier = 2  →  IntegerOrNotDetected value = 2
  → city_tier = 3  →  IntegerOrNotDetected value = 3
  → null           →  "not_detected"
```

---

## 3. Apollo.io

**Trigger:** B2B leads with a company name or email domain. Apollo is the global company intelligence spine.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_company_name` | `str \| None` | `company.name` | `company.name` | — (used for ICP matching) |
| `enriched_company_industry` | `str \| None` | `company.industry` | `company.industry` | `fit.industry_match` |
| `enriched_company_size` | `int \| None` | `company.size_employees` | `company.size_employees` | `fit.company_size_fit` |
| `enriched_person_role` | `str \| None` | `company.role` | `company.role` | `fit.role_relevance` |
| `enriched_email` | `str \| None` | `lead.email` | `lead.email` | — (used in deduplication + follow-up) |
| `enriched_company_revenue_usd` | `int \| None` | `company.annual_revenue_usd` | — (not in INPUT_SCHEMA directly; informs company_size_fit signal) | `fit.company_size_fit` |
| `enriched_company_founded_year` | `int \| None` | `company.founded_year` | — | — |
| `enriched_company_hq_country` | `str \| None` | `company.hq_country` | — | `fit.serviceability` |

**Signal computation:**

```
fit.industry_match:
  Compare company.industry (from Apollo) against ICP industry list in PersonaObject
  → industry in ICP list       → true
  → industry not in ICP list   → false
  → Apollo returned null       → "not_detected"

fit.role_relevance:
  Compare company.role (from Apollo) against ICP target_roles in PersonaObject
  → exact or fuzzy match to a target_role  → true
  → no match                               → false
  → null (role unknown)                    → "not_detected"

fit.company_size_fit:
  Compare company.size_employees (from Apollo) against ICP company_size_preference
  → within ICP range    → true
  → partial match       → "partial"
  → outside ICP range   → false
  → null                → "not_detected"
```

---

## 4. Surepass (B2B India — GST / CIN / PAN)

**Trigger:** B2B India leads only. Requires GSTIN, CIN, or PAN extracted from message or form.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_gst_registered` | `bool` | `company.gst_registered` | — | `fit.company_size_fit` (B2B India verification) |
| `enriched_gst_status` | `str \| None` | `company.gst_status` | — | `fit.company_size_fit` (active = positive) |
| `enriched_gst_turnover_slab` | `str \| None` | `company.gst_turnover_slab` | — | `fit.company_size_fit` (size proxy) |
| `enriched_company_type` | `str \| None` | `company.legal_type` | — | `fit.industry_match` (type classification) |
| `enriched_paid_up_capital` | `int \| None` | `company.paid_up_capital_inr` | — | `fit.company_size_fit` |
| `enriched_incorporation_date` | `str \| None` | `company.incorporated_at` | — | — |
| `enriched_directors` | `list[str]` | `company.directors` | — | `fit.role_relevance` (verify decision-maker name) |
| `enriched_msme_registered` | `bool` | `company.msme_registered` | — | `fit.company_size_fit` (micro/small = lower size fit for enterprise ICP) |
| `enriched_msme_category` | `str \| None` | `company.msme_category` | — | `fit.company_size_fit` |
| `company.registration_id` (combined) | `str \| None` | `company.registration_id` | `company.registration_id` | — |

**`company.registration_id` assembly (preference order):**
1. CIN (from MCA CIN API) — most authoritative
2. GSTIN (from GST Verification API) — if CIN unavailable
3. PAN (from PAN to Company API) — fallback

**Signal computation:**

```
fit.company_size_fit contribution from Surepass:
  If enriched_gst_turnover_slab is present:
    "0–40L"    → very small → false for enterprise ICP, true for SMB ICP
    "40L–1.5Cr" → small → partial for enterprise, true for SMB
    "1.5Cr–5Cr" → mid-size → true for both
    "5Cr+"     → large → true for enterprise
  If msme_registered = true AND msme_category = "Micro" → very small
  Signal value is "partial" if size is borderline; "not_detected" if all sources return null
```

---

## 5. Probe42 (B2B India — Financial Depth)

**Trigger:** B2B India leads after company identity confirmed by Apollo or Surepass.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_probe_score` | `float \| None` | `company.probe_score` | — | `fit.company_size_fit` (financial health proxy) |
| `enriched_net_worth` | `int \| None` | `company.net_worth_inr` | — | `fit.company_size_fit` |
| `enriched_annual_turnover_inr` | `int \| None` | `company.annual_turnover_inr` | — | `fit.company_size_fit` |
| `enriched_ebitda` | `int \| None` | `company.ebitda_inr` | — | `fit.company_size_fit` |
| `enriched_legal_cases_count` | `int` | `company.legal_cases_count` | — | `fit.company_size_fit` (risk modifier) |
| `enriched_epfo_employee_count` | `int \| None` | `company.epfo_employee_count` | `company.size_employees` (override if Apollo null) | `fit.company_size_fit` |
| `enriched_gst_filing_regularity` | `str \| None` | `company.gst_filing_regularity` | — | `fit.company_size_fit` (operational health) |
| `enriched_probe42_found` | `bool` | `company.probe42_found` | — | — |

**Signal computation:**

```
fit.company_size_fit (Probe42 contributes):
  probe_score >= 4.0  → strong financial signal → true
  probe_score >= 3.0  → stable                  → "partial"
  probe_score >= 2.0  → moderate risk           → "partial"
  probe_score < 2.0   → high risk               → false
  probe42_found = false → signal unchanged from Apollo/Surepass values

company.size_employees override:
  If Apollo returned null AND epfo_employee_count is not null:
    company.size_employees = epfo_employee_count
```

---

## 6. Tracxn (B2B Global — Startup / Funding Intelligence)

**Trigger:** B2B leads (all countries) after company confirmed by Apollo.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_company_stage` | `str \| None` | `company.funding_stage` | — | `context.account_growth_signal` |
| `enriched_total_funding_usd` | `int \| None` | `company.total_funding_usd` | — | `context.account_growth_signal` |
| `enriched_last_funding_round` | `str \| None` | `company.last_funding_round` | — | `context.account_growth_signal` |
| `enriched_last_funding_date` | `str \| None` | `company.last_funding_date` | — | `context.account_growth_signal` |
| `enriched_last_funding_amount_usd` | `int \| None` | `company.last_funding_amount_usd` | — | `context.account_growth_signal` |
| `enriched_investors` | `list[str] \| None` | `company.investors` | — | — |
| `enriched_tracxn_score` | `float \| None` | `company.tracxn_score` | — | — |
| `enriched_tracxn_found` | `bool` | `company.tracxn_found` | — | — |

**Signal computation:**

```
context.account_growth_signal:
  Determined by combining funding_stage + last_funding_date recency:

  funding_stage:
    "Late-Stage Funded" → budget_signal = 1.0
    "Early-Stage Funded" → budget_signal = 0.75
    "Seed" → budget_signal = 0.5
    "Unfunded" → budget_signal = 0.25
    "Acquired" → budget_signal = 0.6

  last_funding_date recency (days since):
    ≤ 90 days → recency_multiplier = 1.0   (HOT signal)
    ≤ 180 days → recency_multiplier = 0.8
    ≤ 365 days → recency_multiplier = 0.5
    > 365 days → recency_multiplier = 0.2

  combined_score = budget_signal × recency_multiplier
  → combined_score ≥ 0.7 → true
  → combined_score ≥ 0.4 → (partial — not directly in signal set; rounds to true or false per tenant signal config)
  → combined_score < 0.4 → false
  → tracxn_found = false AND no other growth signal → "not_detected"
```

---

## 7. NewsCatcherAPI (B2B — Company News Intelligence)

**Trigger:** B2B leads after company identity confirmed, company size > 50 employees or funding_stage not null.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_news_count_90d` | `int` | `company.news_count_90d` | — | `context.account_growth_signal` |
| `enriched_news_sentiment_avg` | `float \| None` | `company.news_sentiment_avg` | — | `context.account_growth_signal` |
| `enriched_news_sentiment_label` | `str \| None` | `company.news_sentiment_label` | — | `context.account_growth_signal` |
| `enriched_news_themes` | `list[str] \| None` | `company.news_themes` | — | `context.account_growth_signal` |
| `enriched_news_top_headline` | `str \| None` | `company.news_top_headline` | — | — (injected into salesperson context) |
| `enriched_news_top_date` | `str \| None` | `company.news_top_date` | — | — |

**Signal computation:**

```
context.account_growth_signal contribution from NewsCatcherAPI:
  (combined with Tracxn signal — both contribute, final value is max of the two)

  news_themes contains any of {funding, expansion, award, partnership, launch}:
    → positive growth signal → true
  news_themes contains any of {layoffs, bankruptcy, lawsuit, fraud, restructuring}:
    → negative growth signal → false
  news_sentiment_avg > 0.5 AND news_count_90d > 5 → true
  news_sentiment_avg < -0.3 → false
  news_count_90d = 0 → no news signal; does not override Tracxn-based value
  news_count_90d = null → "not_detected" (only if Tracxn also not_detected)
```

---

## 8. IndiaMART / JustDial (B2B India — SMB Directory Presence)

**Trigger:** B2B India leads where Apollo and Probe42 returned limited data (likely SMBs not indexed by global providers).

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_indiamart_listed` | `bool` | `company.indiamart_listed` | — | `fit.serviceability` |
| `enriched_indiamart_categories` | `list[str] \| None` | `company.indiamart_categories` | — | `fit.industry_match` (fallback) |
| `enriched_justdial_listed` | `bool` | `company.justdial_listed` | — | `fit.serviceability` |
| `enriched_justdial_rating` | `float \| None` | `company.justdial_rating` | — | `fit.serviceability` |

**Signal computation:**

```
fit.serviceability (IndiaMART/JustDial contribution):
  indiamart_listed = true  → confirmed business presence → "partial" (not full true without geo match)
  justdial_listed = true   → confirmed local business → "partial"
  Both listed              → true (business is verified and locally present)
  Neither listed           → does not override — value stays from Google Places resolution

fit.industry_match (IndiaMART fallback):
  enriched_indiamart_categories vs ICP industry list
  → match found → industry_match = true (only used when Apollo returned null industry)
```

---

## 9. Serper.dev (Last-Resort Fallback)

**Trigger:** All previous providers returned null for `company.name` or `company.industry`. Serper is the fallback of last resort — it runs a Google Search and applies LLM extraction to the results.

| NormalisedEvent field | Type | EnrichedLead property | LLM INPUT_SCHEMA field | Signal driven |
|---|---|---|---|---|
| `enriched_serper_company_name` | `str \| None` | `company.name` (override if still null) | `company.name` | `fit.industry_match` |
| `enriched_serper_industry_guess` | `str \| None` | `company.industry` (override if still null) | `company.industry` | `fit.industry_match` |
| `enriched_serper_confidence` | `float` | `company.serper_confidence` | — | Controls signal detection threshold (< 0.5 → treat as not_detected; no completeness penalty) |
| `enriched_serper_source_url` | `str \| None` | `company.serper_source_url` | — | — |

**Signal computation:**

```
fit.industry_match (Serper fallback):
  Same as Apollo computation — compare industry_guess against ICP industry list
  Serper_confidence < 0.5 → treat as "not_detected" (too uncertain to score)
  Serper_confidence ≥ 0.5 → signal detected; scored normally

Note: No flat completeness penalty for Serper use (removed — team decision 2026-05-22).
lead_completeness = detected_signals / total_signals across all providers.
If Serper_confidence < 0.5, those signals count as not_detected, which already reduces
completeness naturally via the formula.
```

---

## Signal Coverage by Source

Which signals require which providers to be enabled (feature flag):

| Signal | `derived_metrics.signal_values` | Required providers | Falls back to |
|---|---|---|---|
| `fit.industry_match` | boolean | `enrichment.apollo` | Serper (if Apollo disabled or null) → `not_detected` |
| `fit.role_relevance` | boolean | `enrichment.apollo` | `not_detected` |
| `fit.company_size_fit` | boolean / partial | `enrichment.apollo` + optionally `enrichment.probe42` | Apollo alone is sufficient; Probe42 refines |
| `fit.serviceability` | boolean / partial | `enrichment.google_places` | Truecaller carrier country → `partial` |
| `context.geography_tier` | integer 1–3 | `enrichment.google_places` | `not_detected` |
| `context.account_growth_signal` | boolean | `enrichment.tracxn` and/or `enrichment.newscatcher` | Either alone is sufficient; both = higher accuracy |
| `context.seasonal_relevance` | enum | Internal calendar logic — **no enrichment provider** | Always computable; never `not_detected` |
| `behaviour.prior_customer` | boolean | CRM sync — **no enrichment provider** | `not_detected` if no CRM connected |
| `behaviour.referral_source` | enum | Source attribution — **no enrichment provider** | Derived from `lead.source` field at ingest |
| `intent.*` (all 5 signals) | boolean | Message Parser (Haiku, DM path) / form fields (Lead Ad) | `not_detected` if message parsing fails |
| `engagement.*` (all 5 signals) | mixed | Behavioral tracking at ingest — **no enrichment provider** | Partial `not_detected` if single-message lead |

---

## Field Availability Summary — LLM INPUT_SCHEMA

| LLM INPUT_SCHEMA field | Available | Primary provider | Secondary provider | Null when |
|---|---|---|---|---|
| `lead.name` | Yes | Truecaller | Message Parser | Both return null |
| `lead.phone` | Always | Ingest | — | Never null (required at ingest) |
| `lead.email` | Conditional | Apollo | Form fields | B2C + no form submission |
| `lead.channel` | Always | Ingest | — | Never null |
| `lead.source` | Always | Ingest | — | Never null |
| `lead.first_contact_date` | Always | Ingest | — | Never null |
| `lead.geography` | Conditional | Google Places | Truecaller carrier country | Neither resolves |
| `lead.city_tier` | Conditional | Google Places | — | Geography unknown |
| `company.name` | Conditional | Apollo | Surepass / Serper | B2C + no company name in message |
| `company.industry` | Conditional | Apollo | IndiaMART / Serper | Company not found in any provider |
| `company.size_employees` | Conditional | Apollo | Probe42 (EPFO) | Company not found or micro-business |
| `company.role` | Conditional | Apollo | Message Parser | Lead did not disclose role |
| `company.registration_id` | Conditional | Surepass | — | Non-India or B2C lead |
| `persona.tone` | Per-tenant | PersonaObject | — | Tenant did not specify tone |
| `persona.custom_rules` | Per-tenant | PersonaObject | — | Tenant has no custom rules (empty array) |
| All `persona.*` fields except tone/custom_rules | Always | PersonaObject | — | Never null (pre-flight check blocks scoring) |
| All `behavior.*` fields | Always | Ingest + behavioral tracking | — | `revisit_count = 0` for Lead Ads |
| All `derived_metrics.*` fields | Always | Signal extraction layer | — | `not_detected` for unavailable signals |

---

## Write Order and Lineage

Following the system-wide write order rule:

```
P1-S4 (Lead Enrichment):
  1. Provider call completes → NormalisedEvent fields written
  2. lineage_record written (provider, fields returned, cost, latency)
  3. EnrichedLead object assembled
  4. pipeline_stage → "enriched" (LAST WRITE — crash recovery point)

P1-S5 (Normalise):
  1. EnrichedLead → NormalisedLead (field cleaning, lead_completeness calculation)
  2. signal_values computed from NormalisedLead
  3. lineage_record written
  4. pipeline_stage → "normalised" (LAST WRITE)
```

A crash after provider call but before `pipeline_stage = "enriched"` resumes from `captured` or `fetched` — the enrichment step re-runs from scratch. Provider caching (company cache TTL) prevents duplicate API costs on re-runs.

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| `wiki/analyses/llm-io-contract.md` | Authoritative INPUT_SCHEMA; final column in this map |
| `wiki/analyses/enrichment-tools-integration.md` | Source for Surepass, Probe42, Tracxn, NewsCatcherAPI, Serper provider details |
| `wiki/analyses/pipeline-io-contracts.md` | P1-S4 and P1-S5 I/O shapes; EnrichedLead and NormalisedLead types |
| `wiki/analyses/orchestration-layer-spec.md` §6.3 | Feature Flag Enforcement — controls which providers are enabled per tenant |
| `wiki/analyses/signal-detection-rule-spec.md` | Signal extraction rules (deterministic) that produce signal_values from EnrichedLead |
