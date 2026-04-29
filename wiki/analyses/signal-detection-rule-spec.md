---
type: analysis
question: "What is the format and execution model for signal detection_rules?"
date: 2026-04-28
tags: [signals, detection-rule, enrichment, normalised-event, extractor, pipeline-1, hard-blocker-resolved]
sources_consulted:
  - "[[concepts/signal-types]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/execution-type-classification]]"
status: COMPLETE — resolves hard blocker on Lead Enrichment code
---

# Signal Detection Rule — Specification

**Question:** What is the format and execution model for `signal.detection_rule`?
**Date:** 2026-04-28
**Status:** RESOLVES the hard blocker flagged across orchestration-layer-spec, execution-type-classification, persona-agent-spec, tech-stack-research, service-scaling-strategy, and overview.

---

## Why This Was a Hard Blocker

The `signal.detection_rule` field is what makes Lead Enrichment (P1-2b) work. Without a defined format:
- The Persona Agent (Step 3) could not output executable signal definitions
- The enrichment service could not evaluate signals deterministically
- The 1-LLM-call-per-lead guarantee was fragile (risk of shifting P1-2b from AUTOMATION to HYBRID)
- No enrichment code could be written

This document resolves all of the above.

---

## Prerequisite: NormalisedEvent Schema

`detection_rule.source_fields` references field paths on a normalized event record. All event sources (form, DM, ad, website) are normalized into this shape before Pipeline 1 runs. This is the minimal schema for MVP — enough to cover all signal types in the extractor vocabulary.

```python
class NormalisedEvent:
    # Identity
    lead_id: str
    tenant_id: str

    # Source
    source_type: Literal[
        "google_form", "website_visit", "instagram_dm",
        "facebook_dm", "whatsapp_dm", "meta_ads_lead",
        "google_ads_lead", "snapchat_ads_lead", "manual"
    ]

    # Text content — present depending on source
    message_content: str | None        # DMs, WhatsApp
    form_response: dict[str, str] | None  # field name → value
    search_query: str | None           # website search

    # Website behaviour — present for website_visit only
    page_url: str | None
    page_type: Literal["pricing", "case_study", "product", "home", "other"] | None
    time_on_page_seconds: int | None

    # Attribution
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    ad_campaign_id: str | None
    ad_set_id: str | None

    # Lead identity — populated at normalisation from all available sources
    email: str | None
    phone: str | None
    social_profile_id: str | None

    # Enriched fields — populated by external enrichment API calls
    enriched_job_title: str | None
    enriched_company_size: int | None
    enriched_industry: str | None
    enriched_geography: str | None

    # Timestamps
    event_timestamp: datetime
    received_at: datetime
```

All detection rules reference fields from this schema by name. `source_fields` paths use dot notation for nested access (e.g., `form_response.message`).

---

## The detection_rule Schema

Three-field structure. Every signal carries exactly one detection_rule.

```json
{
  "type": "keyword_match",
  "source_fields": ["message_content", "form_response.message"],
  "params": {
    "keywords": ["price", "pricing", "cost", "quote", "how much"],
    "match_mode": "any",
    "threshold": 1
  }
}
```

| Field | Type | Role |
|---|---|---|
| `type` | string | Which pre-built extractor to run. Must be from the vocabulary table below. The Persona Agent cannot invent new types. |
| `source_fields` | list[string] | Which fields on `NormalisedEvent` (or `lead_history`) to examine. A list — handles the same signal being detectable from multiple sources. |
| `params` | dict | Type-specific configuration (keywords, thresholds, match rules). Kept simple so the Persona Agent can reliably generate them. |

---

## Uniform Output Contract

Every extractor returns exactly this shape. No exceptions.

```python
@dataclass
class ExtractionResult:
    detected: bool      # was the signal present?
    value: float        # 0.0–1.0, signal strength
    evidence: str       # what was found (for lineage and auditability)
```

The `value` (0.0–1.0) is inserted directly into the scoring prompt: `{signal_name}: {value}`.

**Why 0.0–1.0 and not boolean?** Some signals have natural gradation (3 keyword matches is stronger than 1; 4 touchpoints is stronger than 1). The float preserves that gradient for the Rating Agent. The `detected: bool` is a convenience flag for routing and lineage — it does not replace `value` in scoring.

**Value normalization is the extractor's responsibility.** If `keyword_match` finds 3 hits, the extractor normalizes: `min(hits / max_expected_hits, 1.0)`. The pipeline never receives raw counts.

---

## Extractor Vocabulary (MVP — 13 types)

These 13 types cover all five scoring dimensions across all event sources. The Persona Agent is given this table in its Step 3 system prompt and constrained to these types.

| Type | Dimension(s) | What it does | Key params |
|---|---|---|---|
| `keyword_match` | Intent, Fit | Searches source_fields for keywords | `keywords`, `match_mode: any/all`, `threshold` |
| `question_pattern` | Intent | Detects question structures (pricing? timeline? scope?) | `patterns: [...]` |
| `urgency_indicator` | Intent | Detects urgency language | `urgency_terms: [...]` |
| `budget_authority_indicator` | Intent | Detects budget/authority language | `terms: [...]` |
| `touchpoint_count` | Engagement | Counts total lead events in DB history | `min_count`, `max_count` (for value scaling) |
| `channel_diversity` | Engagement | Counts distinct `source_type` values in lead history | `min_channels`, `max_channels_for_full_score` |
| `recency_check` | Engagement | Checks how recent the last event was | `full_score_within_hours`, `zero_score_after_days` |
| `page_visit_match` | Behaviour | Checks if `page_type` matches expected pages | `page_types: [...]` |
| `form_completion_depth` | Behaviour | Checks how many form fields were filled | `min_fields_for_full_score` |
| `source_type_match` | Behaviour, Context | Checks if `source_type` is in a list | `source_types: [...]` |
| `utm_match` | Context | Checks UTM fields against expected values | `utm_campaign`, `utm_medium`, `utm_source` |
| `geography_match` | Fit, Context | Checks enriched lead location against ICP geography | `allowed_regions: [...]` |
| `company_attribute_match` | Fit | Checks enriched company data (industry, size, etc.) | `industry: [...]`, `size_range: [min, max]` |

**Rule: one extractor per signal. No composition.**

If a tenant needs "pricing question AND decision-maker role," that is two signals across two dimensions — not one nested rule. The moment AND/OR composition is allowed, a DSL is needed that the LLM must author reliably. That is not tractable. Composition is handled naturally by the multi-signal prompt template.

**Note on stateful extractors:** `touchpoint_count`, `channel_diversity`, and `recency_check` are stateful — they read the lead's prior events from the DB, not just the current event. The enrichment service passes `lead_history: list[NormalisedEvent]` alongside the current event to support these extractors. This makes the enrichment step a DB-reading operation, not a pure function.

---

## Five Worked Examples (One Per Dimension)

### Fit — ICP role match

```json
{
  "name": "icp_role_match",
  "dimension": "fit",
  "description": "Lead's job title matches a target decision-maker or influencer role",
  "weight_within_dim": 0.40,
  "detection_rule": {
    "type": "keyword_match",
    "source_fields": ["enriched_job_title", "form_response.role"],
    "params": {
      "keywords": ["procurement manager", "operations head", "founder", "director"],
      "match_mode": "any",
      "threshold": 1
    }
  }
}
```
Extractor returns: `{detected: true, value: 1.0, evidence: "enriched_job_title='procurement manager'"}`

---

### Intent — Pricing request

```json
{
  "name": "pricing_request",
  "dimension": "intent",
  "description": "Lead explicitly asked for a price quote or pricing information",
  "weight_within_dim": 0.30,
  "detection_rule": {
    "type": "keyword_match",
    "source_fields": ["message_content", "form_response.message"],
    "params": {
      "keywords": ["price", "pricing", "cost", "quote", "how much", "charges"],
      "match_mode": "any",
      "threshold": 1
    }
  }
}
```
Extractor returns: `{detected: true, value: 1.0, evidence: "Found in message_content: 'Can you share your pricing?'"}`

---

### Engagement — Multi-channel presence

```json
{
  "name": "multi_channel_presence",
  "dimension": "engagement",
  "description": "Lead has interacted via more than one channel",
  "weight_within_dim": 0.25,
  "detection_rule": {
    "type": "channel_diversity",
    "source_fields": ["lead_history.source_types"],
    "params": {
      "min_channels": 1,
      "max_channels_for_full_score": 3
    }
  }
}
```
Extractor returns: `{detected: true, value: 0.67, evidence: "2 distinct channels: instagram_dm, meta_ads_lead"}` *(2/3 = 0.67)*

---

### Behaviour — Pricing page visit

```json
{
  "name": "pricing_page_visit",
  "dimension": "behaviour",
  "description": "Lead visited the pricing page on the tenant's website",
  "weight_within_dim": 0.35,
  "detection_rule": {
    "type": "page_visit_match",
    "source_fields": ["page_type"],
    "params": {
      "page_types": ["pricing"]
    }
  }
}
```
Extractor returns: `{detected: true, value: 1.0, evidence: "page_type='pricing'"}`

---

### Context — Targeted paid campaign

```json
{
  "name": "targeted_campaign_lead",
  "dimension": "context",
  "description": "Lead arrived from a targeted paid campaign, not organic",
  "weight_within_dim": 0.50,
  "detection_rule": {
    "type": "source_type_match",
    "source_fields": ["source_type"],
    "params": {
      "source_types": ["meta_ads_lead", "google_ads_lead", "snapchat_ads_lead"]
    }
  }
}
```
Extractor returns: `{detected: true, value: 1.0, evidence: "source_type='meta_ads_lead'"}`

---

## How the Enrichment Service Executes This

Strategy pattern. One class per extractor type. Adding a new signal type = add a new extractor class. No changes to the pipeline.

```python
EXTRACTOR_REGISTRY = {
    "keyword_match": KeywordMatchExtractor,
    "question_pattern": QuestionPatternExtractor,
    "urgency_indicator": UrgencyIndicatorExtractor,
    "budget_authority_indicator": BudgetAuthorityExtractor,
    "touchpoint_count": TouchpointCountExtractor,
    "channel_diversity": ChannelDiversityExtractor,
    "recency_check": RecencyCheckExtractor,
    "page_visit_match": PageVisitMatchExtractor,
    "form_completion_depth": FormCompletionDepthExtractor,
    "source_type_match": SourceTypeMatchExtractor,
    "utm_match": UtmMatchExtractor,
    "geography_match": GeographyMatchExtractor,
    "company_attribute_match": CompanyAttributeMatchExtractor,
}

class LeadEnrichmentService:
    def evaluate_signals(
        self,
        signals: list[Signal],
        event: NormalisedEvent,
        lead_history: list[NormalisedEvent],  # required for stateful extractors
    ) -> list[SignalEvaluation]:
        results = []
        for signal in signals:
            extractor = EXTRACTOR_REGISTRY[signal.detection_rule.type]
            result = extractor.run(signal.detection_rule, event, lead_history)
            results.append(SignalEvaluation(
                signal_id=signal.signal_id,
                lead_id=event.lead_id,
                detected=result.detected,
                value=result.value,
                evidence=result.evidence,
            ))
        return results
```

---

## Why Deterministic Extractors Are Sufficient

The Rating Agent (LLM) sees the raw message content alongside the extracted signal values in the prompt template. Detection rules produce structured anchors (`pricing_request: 1.0`); the LLM does the contextual reasoning on top of those anchors. Semantic strength is not lost by using deterministic extraction — the LLM compensates by reading the full message.

This means there is no need for an `llm_extract` extractor type at MVP. If a signal requires LLM semantic interpretation, it belongs as a dimension in the scoring prompt, not as a detection_rule type.

---

## What Changes in Other Documents

This spec resolves the `[TBD]` in:
- [[analyses/persona-agent-spec]] — Step 3 output schema and Open Decisions: Persona Agent emits detection_rule directly (not a placeholder). Engineering mapping step removed.
- [[analyses/orchestration-layer-spec]] — signal schema and enrichment step: format now defined.
- [[analyses/execution-type-classification]] — Open Question 3 and Follow-up 3: P1-2b AUTOMATION classification is protected; detection_rule is fully deterministic.
- [[analyses/tech-stack-research]] — Open Items #1 and Follow-up #5: hard blocker resolved.
- [[analyses/service-scaling-strategy]] — Caveats: enrichment code can now be written.
- [[concepts/data-entity-model]] — Open Question on `signal` schema: detection_rule format confirmed.
- [[wiki/overview]] — Open Question #1: resolved.

---

## Caveats & Gaps

- **Extractor vocabulary is MVP-scoped.** New signal types in future sprints require adding an extractor class and updating the vocabulary table given to the Persona Agent in its Step 3 prompt.
- **NormalisedEvent schema is minimal.** As new event sources are added, new fields may be needed on `NormalisedEvent`. Detection rules for those sources must reference the new fields.
- **Multi-event leads:** Stateful extractors (`touchpoint_count`, `channel_diversity`, `recency_check`) read `lead_history` from the DB. The enrichment service must fetch this history for every lead before evaluating stateful signals. This is a DB read at enrichment time — factor into latency budget.
- **`enriched_*` fields** are populated by external enrichment API calls earlier in P1-2a (Data Gather). If the external API is unavailable, enriched fields will be null. Extractors that reference `enriched_*` fields must handle null gracefully (return `detected: false, value: 0.0`).

## Follow-up Questions

- Confirm the Persona Agent Step 3 system prompt includes the vocabulary table and 2–3 few-shot examples of valid detection_rules.
- Confirm test coverage plan: unit tests for each extractor class with fixture events covering all source types.
- Define what happens when a `detection_rule.type` is not found in `EXTRACTOR_REGISTRY` at runtime (fail-safe: log error, return `detected: false, value: 0.0`, continue pipeline).
