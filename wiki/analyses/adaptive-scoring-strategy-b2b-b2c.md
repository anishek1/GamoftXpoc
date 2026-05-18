---
type: analysis
question: "How does the scoring system adapt its signals, weights, completeness calculation, ICP structure, and pipeline steps for B2B vs B2C tenants?"
date: 2026-05-18
tags: [b2b, b2c, scoring, adaptive, signals, persona, icp, completeness, pipeline, enrichment]
sources_consulted:
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/signal-detection-rule-spec]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/global-data-collection-architecture]]"
  - "[[concepts/signal-types]]"
  - "[[concepts/persona-layer]]"
  - "[[sources/2026-b2c-data-acquisition]]"
status: COMPLETE
---

# Adaptive Scoring Strategy — B2B vs B2C

**System:** Multi-Tenant Adaptive Lead Intelligence Engine  
**Version:** 1.0.0  
**Date:** 2026-05-18

**Scope:** How the system adapts scoring signals, dimension weights, lead completeness, ICP structure, disqualification rules, bucket thresholds, and enrichment pipeline steps for B2B vs B2C tenants.

---

## 1. The Core Adaptation Mechanism

Every tenant has a `business_type` field on their PersonaObject: `"B2B"` or `"B2C"`. This single field drives all downstream adaptation — it is not a hint, it is a **hard mode selector** that governs signal applicability, completeness formula, ICP structure, disqualification rules, and enrichment path.

`business_type` is set at Pipeline 2 Step 1 (Persona Agent) and **cannot be changed without a full Persona Agent re-run.** It is locked for the lifetime of a persona version.

---

## 2. Signal Differences

### 2.1 Default Signal Set by Mode

Each signal has an `applicable_to` tag: `B2B` | `B2C` | `both`. The Persona Agent (Step 3) must only emit signals whose `applicable_to` matches the tenant's `business_type` (or is `both`).

**Enforcement rule:** The orchestrator validates each signal in the tenant's signal registry against `persona.business_type` when generating the prompt template. Any signal tagged `B2B` in a `B2C` tenant's registry → `PersonaInvalidError`, halt onboarding.

| Dimension | Representative B2B signals | Representative B2C signals | Shared |
|---|---|---|---|
| **Fit** | `industry_match`, `role_relevance`, `company_size_fit` | `interest_category_match`, `demographic_fit` | `serviceability`, `geography_tier` |
| **Intent** | `pricing_request`, `demo_requested`, `rfq_language`, `timeline_stated` | `purchase_language`, `cart_signal`, `wishlist_activity`, `urgency_language` | `budget_mentioned` |
| **Engagement** | `response_speed`, `channel_diversity`, `conversation_depth` | `response_speed`, `conversation_depth`, `social_interaction` | `revisit_count`, `follow_up_initiated` |
| **Behaviour** | `prior_customer`, `referral_source`, `content_engagement` | `repeat_purchase_history`, `loyalty_membership`, `review_activity` | `form_completion` |
| **Context** | `account_growth_signal`, `seasonal_relevance` | `seasonal_relevance`, `promotional_campaign_active` | `geography_tier` |

### 2.2 Default Dimension Weights by Mode

Default weights are starting points. Persona Agent (Step 1) may adjust per-tenant based on business description.

| Dimension | B2B default | B2C default | Rationale |
|---|---|---|---|
| Fit | 0.25 | 0.20 | B2B: company/role fit is a hard prerequisite. B2C: fit is softer (interest-based) |
| Intent | 0.25 | 0.25 | Equal — explicit purchase intent matters in both modes |
| Engagement | 0.20 | 0.20 | Equal |
| Behaviour | 0.20 | 0.25 | B2C: purchase history and loyalty are stronger predictors than in B2B |
| Context | 0.10 | 0.10 | Equal |

**Constraint:** Weights must sum to 1.0 regardless of mode. PersonaInvalidError if violated. See [[analyses/llm-io-contract]] WEIGHT_SUM rule.

---

## 3. ICP Structure by Mode

The `IcpDefinition` output of Persona Agent Step 2 has mode-specific sub-fields. The Persona Agent emits only the fields relevant to the tenant's `business_type`.

### B2B ICP Structure
```json
{
  "icp_description": "narrative string",
  "target_segment": {
    "industry":        "e.g. SaaS / Cloud Software",
    "company_size":    "e.g. 50–500 employees",
    "funding_stage":   "e.g. Series A–C",
    "geography":       "e.g. India Tier 1 cities",
    "role_profile":    "e.g. CTO, Head of Sales, VP Engineering"
  },
  "priority_signals":        ["pricing_request", "demo_requested", "role_relevance"],
  "disqualifying_signals":   ["student_or_intern", "no_sales_team", "reseller_intent"],
  "buying_triggers":         ["fundraise announcement", "headcount growth", "competitor switch"],
  "icp_examples":            ["string"]
}
```

### B2C ICP Structure
```json
{
  "icp_description": "narrative string",
  "target_segment": {
    "interest_category": "e.g. organic skincare, health supplements",
    "demographic":       "e.g. women 25–45, health-conscious buyers",
    "geography":         "e.g. India metro cities",
    "purchase_frequency": "e.g. repeat buyers, monthly reorder"
  },
  "priority_signals":        ["repeat_purchase_history", "urgency_language", "interest_category_match"],
  "disqualifying_signals":   ["bot_pattern", "bulk_reseller", "returns_abuse_history"],
  "buying_triggers":         ["seasonal event", "promotional campaign", "product restock"],
  "icp_examples":            ["string"]
}
```

**Note:** `company_size` and `funding_stage` do not appear in B2C ICP. `interest_category` and `demographic` do not appear in B2B ICP. The Persona Agent must not mix these.

---

## 4. Lead Completeness Formula by Mode

The `lead_completeness` score (0.0–1.0) measures what fraction of expected signal fields were populated for this lead. "Expected" is mode-dependent.

### Expected Fields by Mode

| Field group | B2B expected? | B2C expected? |
|---|---|---|
| `lead.name` | Yes | Yes |
| `lead.phone` | Yes | Yes |
| `lead.email` | Optional (0.5 weight) | Optional (0.5 weight) |
| `company.name` | **Yes (required)** | No |
| `company.industry` | **Yes (required)** | No |
| `company.role` | **Yes (required)** | No |
| `company.size_employees` | Optional (0.5 weight) | No |
| `lead.geography` | Optional (0.5 weight) | Optional (0.5 weight) |
| `lead.city_tier` | Optional (0.5 weight) | Optional (0.5 weight) |
| All signal values present (not `not_detected`) | Partial weight per signal | Partial weight per signal |

**B2B completeness formula:** Missing `company.name`, `company.industry`, or `company.role` each reduce completeness by a fixed penalty (0.15 per field). A B2B lead with no company information has completeness ≤ 0.55.

**B2C completeness formula:** Company fields contribute 0 to completeness calculation. A B2C lead is not penalised for absent company data.

**Implementation:** The Normalise step (P1-3) computes `lead_completeness` using the tenant's `business_type` from the PersonaObject. The same normalise step is used for both modes — the formula branches on `business_type`.

---

## 5. Disqualification Gate Rules by Mode

The Disqualification Gate (P1-6) applies hard overrides before bucketing. Disqualifying conditions differ by mode.

| Disqualifier | B2B | B2C | Action |
|---|---|---|---|
| `student_or_intern` signal detected | Yes | No | Score → 0, bucket → COLD |
| `no_sales_team` signal detected | Yes | No | Score → 0, bucket → COLD |
| `reseller_intent` signal detected | Yes | No | Score → 0, bucket → COLD |
| `bot_pattern` signal detected | No | Yes | Score → 0, bucket → COLD |
| `returns_abuse_history` signal detected | No | Yes | Score multiplied by 0.5 (soft penalty) |
| `geography_out_of_scope` signal detected | Both | Both | Score → 0, bucket → COLD |
| `lead_completeness < needs_review threshold` | Both | Both | `needs_review = true`, route to human review |

The Persona Agent (Step 2) populates `IcpDefinition.disqualifying_signals`. These are loaded into the Disqualification Gate at scoring time. Tenants may define custom disqualifiers beyond the list above — the Gate reads from the tenant's ICP, not a hardcoded list.

---

## 6. Bucket Thresholds by Mode

Default starting thresholds differ by mode, reflecting different conversion dynamics.

| Bucket | B2B default | B2C default | Rationale |
|---|---|---|---|
| HOT minimum | 80 | 75 | B2C conversion is faster — lower threshold appropriate for higher-volume channels |
| WARM minimum | 55 | 50 | B2C: broader "warm" band captures more actionable leads |
| COLD | < 55 | < 50 | |

These are **starting points only**. Persona Agent Step 1 may propose different thresholds based on business description (e.g., a high-ticket B2C product may use thresholds closer to B2B). Thresholds are stored in `PersonaObject.banding` and recalibrated after Month 1 using the AP1 metric (Bucket Outcome Rate).

**Enforcement:** The Output Schema Layer enforces thresholds from the PersonaObject — not from a global constant. If the Persona Agent sets a tenant's `hot_min = 70`, the threshold is 70 for that tenant, regardless of the mode default.

---

## 7. Enrichment Pipeline Adaptation

Pipeline 1 enrichment steps differ by mode to avoid unnecessary API calls and cost.

| Enrichment step | B2B | B2C | Notes |
|---|---|---|---|
| Company disambiguation (Probe42, Apollo) | Yes | No | Company lookup irrelevant for individual B2C leads |
| Account graph check | Yes | No | Existing relationship at company level — B2B only |
| Individual identity enrichment (Truecaller) | No (phone prefix only) | Yes | B2C: individual name/location from phone is valuable |
| Historical order data fetch | No | Yes | B2C: purchase history from Shopify/WooCommerce API |
| LinkedIn profile enrichment | Yes | No | B2B: professional profile signals |
| Instagram follower/profile enrichment | Yes (brand B2B) | Yes | Both can use Instagram signals |
| GST/company registration check | Yes (India B2B) | No | Company legitimacy — B2B only |

The capability registry (see [[analyses/orchestration-layer-spec]]) stores which enrichment steps are active per tenant. The `business_type` field drives the default capability set at tenant onboarding. Tenants may add or remove capabilities post-onboarding.

---

## 8. Conversation Intelligence Adaptation

The Message Parser (Haiku) on the DM path uses a mode-aware extraction prompt. The fields it extracts differ by `business_type`:

| Extracted field | B2B | B2C |
|---|---|---|
| Contact name | Yes | Yes |
| Company name | Yes | No |
| Job title / role | Yes | No |
| Purchase intent language | Yes | Yes |
| Product interest / category | No | Yes |
| Urgency signals | Yes | Yes |
| Budget / price inquiry | Yes | Yes |
| Demographic cues | No | Yes |

The Message Parser prompt is built at tenant onboarding time and stored in `prompt_registry` alongside the Rating Agent prompt. It follows the same four-section template framework (see [[analyses/prompt-template-framework]]) with B2B/B2C-appropriate field extraction instructions in the CONTEXT section.

---

## 9. Tenant Validation at Onboarding

At Pipeline 2 completion, before the tenant is activated, the system validates B2B/B2C consistency:

| Check | Failure action |
|---|---|
| All signals in registry have `applicable_to` matching `business_type` or `both` | PersonaInvalidError, halt activation |
| B2B tenants have at least one company-level signal in the Fit dimension | Warning logged; team lead notified |
| B2C tenants have no company-level signals in Fit (e.g., `company_size_fit`) | PersonaInvalidError — remove signal or re-run |
| ICP structure fields match mode (no `company_size` in B2C ICP) | PersonaInvalidError — Persona Agent must re-run Step 2 |
| `banding.hot_min > banding.warm_min` | PersonaInvalidError, halt |

---

## Open Decisions

| Decision | Status |
|---|---|
| B2C bucket threshold defaults (75/50) | Proposed above — confirm with Urvee Organics POC data after Month 1 |
| Lead completeness penalty per missing B2B company field (0.15 each) | Proposed — adjust after Phase 0 data reveals typical B2B enrichment success rate |
| Whether to support `Hybrid` business_type (B2B company with B2C products) | Currently `B2B` or `B2C` only. Hybrid support deferred — requires custom signal mixing logic. |
| Message Parser prompt per mode storage | Stored in `prompt_registry` alongside Rating Agent prompt — confirm prompt_registry can hold multiple template types per tenant |
