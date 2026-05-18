---
type: analysis
question: "What are the strict, machine-consumable LLM input and output JSON contracts for the Rating Agent, including schema validation rules?"
date: 2026-05-05
last_updated: 2026-05-18
tags: [rating-agent, scoring, schema, validation, json-contract, input-contract, output-contract, pipeline-1]
sources_consulted:
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/prompt-template-framework]]"
  - "[[analyses/context-construction-specification]]"
  - "[[concepts/signal-types]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/confidence-first-class]]"
  - "[[analyses/orchestration-layer-spec]]"
status: COMPLETE
---

# LLM I/O Contract — Rating Agent

**System:** Multi-Tenant Adaptive Lead Intelligence Engine  
**Version:** 1.1.0 (revised 2026-05-18)  
**Date:** 2026-05-05 | **Revised:** 2026-05-18

**Scope:** Machine-consumable INPUT_SCHEMA, OUTPUT_SCHEMA, and VALIDATION_RULES for the Rating Agent LLM call. This contract is the authoritative specification for the boundary between data enrichment (Pipeline 1 Steps 0–12) and the LLM scoring call (Step 13).

---

## Plain-English Summary

**Why this exists:** When the system sends data to the AI model and receives a score back, both sides must agree on the exact format — what fields to send, what types they must be, and what the response must look like. Without this agreement, the AI might return a score as text ("eighty-six") instead of a number (86), or skip a required field, and the system would either crash or silently store wrong data. This document is the precise contract both sides must follow.

**How it works:** Three JSON schemas work together. INPUT_SCHEMA defines every field the system must send. OUTPUT_SCHEMA defines the 7 fields the LLM must return. VALIDATION_RULES define what constitutes a valid input or output, including cross-field rules (e.g., sub-scores must sum to total score) and retry/fallback behaviour.

---

## Design Decisions

| Field | Previous spec | This contract | Reason |
|---|---|---|---|
| `reasoning` | Freeform string | Structured object (4 sub-fields) | Enables machine parsing; eliminates freeform blob ambiguity. **Prompt OUTPUT FORMAT section must use the structured schema below — breaking change.** |
| `recommended_action` | One-sentence string | Enum of 7 values | Deterministic parsing; eliminates LLM hallucination of novel action verbs. **Prompt OUTPUT FORMAT section must list the 7 enum values explicitly.** |
| Signal value types | Described in prose | Discriminated union per signal class | Prevents type confusion between `false` (detected, negative) and `"not_detected"` (not evaluated) |
| `confidence` (legacy term) | Used in intelligence layer design doc | `lead_completeness` in this contract | RESOLVED 2026-04-22: this is data completeness, not LLM self-confidence (see [[concepts/confidence-first-class]]) |
| `context_inputs` | Required with nullable fields | Optional object; nullable fields removed from `required` | Fields that must be null for `variant=new` must not be in `required` — contradiction resolved |

---

## INPUT_SCHEMA

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "LLMInputContract",
  "description": "Complete structured input passed to the Rating Agent for one lead scoring call.",
  "type": "object",
  "required": [
    "schema_version",
    "tenant_id",
    "lead_id",
    "variant",
    "prompt_template_version",
    "lead",
    "persona",
    "behavior",
    "derived_metrics",
    "context_inputs"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^v\\d+\\.\\d+$",
      "description": "Input schema version, e.g. 'v1.1'"
    },
    "tenant_id": {
      "type": "string",
      "format": "uuid"
    },
    "lead_id": {
      "type": "string",
      "format": "uuid"
    },
    "variant": {
      "type": "string",
      "enum": ["new", "returning", "rescore"]
    },
    "prompt_template_version": {
      "type": "string",
      "pattern": "^v\\d+\\.\\d+\\.\\d+$"
    },
    "lead": {
      "type": "object",
      "required": ["phone", "channel", "source", "first_contact_date"],
      "additionalProperties": false,
      "properties": {
        "name":               { "type": ["string", "null"], "minLength": 1 },
        "phone":              { "type": "string", "pattern": "^\\+[1-9]\\d{6,14}$" },
        "email":              { "type": ["string", "null"], "format": "email" },
        "channel":            { "type": "string", "enum": ["whatsapp", "instagram_dm", "facebook_dm", "lead_ad", "website_form", "linkedin"] },
        "source":             { "type": "string", "minLength": 1 },
        "first_contact_date": { "type": "string", "format": "date" },
        "geography":          { "type": ["string", "null"] },
        "city_tier":          { "type": ["integer", "null"], "minimum": 1, "maximum": 3 }
      }
    },
    "company": {
      "type": "object",
      "additionalProperties": false,
      "description": "Company fields. Required for B2B tenants (enforced by COMPANY_B2B_REQUIRED cross-field rule). Optional for B2C.",
      "properties": {
        "name":            { "type": ["string", "null"], "minLength": 1 },
        "industry":        { "type": ["string", "null"], "minLength": 2 },
        "size_employees":  { "type": ["integer", "null"], "minimum": 0 },
        "role":            { "type": ["string", "null"], "minLength": 1 },
        "registration_id": { "type": ["string", "null"] }
      }
    },
    "persona": {
      "type": "object",
      "required": [
        "tenant_name",
        "business_type",
        "icp_summary",
        "disqualifying_profiles",
        "scoring_weights",
        "hot_min",
        "warm_min",
        "persona_version"
      ],
      "additionalProperties": false,
      "properties": {
        "tenant_name":            { "type": "string", "minLength": 1 },
        "business_type":          { "type": "string", "enum": ["B2B", "B2C"] },
        "icp_summary":            { "type": "string", "minLength": 20, "maxLength": 2000 },
        "disqualifying_profiles": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 5 } },
        "scoring_weights": {
          "type": "object",
          "required": ["fit", "intent", "engagement", "behaviour", "context"],
          "additionalProperties": false,
          "properties": {
            "fit":        { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "intent":     { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "engagement": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "behaviour":  { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "context":    { "type": "number", "minimum": 0.0, "maximum": 1.0 }
          }
        },
        "hot_min":        { "type": "integer", "minimum": 1, "maximum": 100 },
        "warm_min":       { "type": "integer", "minimum": 1, "maximum": 100 },
        "persona_version": { "type": "string", "pattern": "^v\\d+\\.\\d+\\.\\d+$" }
      }
    },
    "behavior": {
      "type": "object",
      "required": ["revisit_count", "channel_diversity", "conversation_depth", "follow_up_initiated"],
      "additionalProperties": false,
      "properties": {
        "revisit_count":        { "type": "integer", "minimum": 0, "description": "Number of separate interaction events. 0 is valid for Lead Ad form submissions with no prior conversation." },
        "channel_diversity":    { "type": "string", "enum": ["single", "multi"] },
        "conversation_depth":   { "type": "string", "enum": ["low", "medium", "high"] },
        "follow_up_initiated":  { "type": "boolean" },
        "response_speed":       { "type": ["string", "null"], "enum": ["fast", "medium", "slow", null] },
        "touchpoints": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["date", "channel", "direction", "summary"],
            "additionalProperties": false,
            "properties": {
              "date":      { "type": "string", "format": "date" },
              "channel":   { "type": "string", "enum": ["whatsapp", "instagram_dm", "facebook_dm", "email", "call", "website"] },
              "direction": { "type": "string", "enum": ["inbound", "outbound"] },
              "summary":   { "type": "string", "minLength": 1, "maxLength": 200 }
            }
          }
        }
      }
    },
    "derived_metrics": {
      "type": "object",
      "required": ["lead_completeness", "signal_values"],
      "additionalProperties": false,
      "properties": {
        "lead_completeness": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "signal_values": {
          "type": "object",
          "description": "Signal values keyed by dimension. Keys within each dimension are tenant-configurable (see SIGNAL_ALL_PRESENT rule). The properties below show Gamoft default signals — other tenants may define different signal keys via the Persona Agent.",
          "required": ["fit", "intent", "engagement", "behaviour", "context"],
          "additionalProperties": false,
          "properties": {
            "fit": {
              "type": "object",
              "required": ["industry_match", "role_relevance", "company_size_fit", "serviceability"],
              "additionalProperties": true,
              "properties": {
                "industry_match":   { "$ref": "#/$defs/BooleanSignal" },
                "role_relevance":   { "$ref": "#/$defs/BooleanSignal" },
                "company_size_fit": { "$ref": "#/$defs/BooleanOrPartialSignal" },
                "serviceability":   { "$ref": "#/$defs/BooleanOrPartialSignal" }
              }
            },
            "intent": {
              "type": "object",
              "required": ["pricing_request", "demo_requested", "urgency_language", "timeline_stated", "budget_mentioned"],
              "additionalProperties": true,
              "properties": {
                "pricing_request":  { "$ref": "#/$defs/BooleanSignal" },
                "demo_requested":   { "$ref": "#/$defs/BooleanSignal" },
                "urgency_language": { "$ref": "#/$defs/BooleanSignal" },
                "timeline_stated":  { "$ref": "#/$defs/BooleanSignalWithNote" },
                "budget_mentioned": { "$ref": "#/$defs/BooleanSignal" }
              }
            },
            "engagement": {
              "type": "object",
              "required": ["response_speed", "revisit_count", "channel_diversity", "conversation_depth", "follow_up_initiated"],
              "additionalProperties": true,
              "properties": {
                "response_speed":      { "$ref": "#/$defs/SpeedSignal" },
                "revisit_count":       { "$ref": "#/$defs/IntegerOrNotDetected" },
                "channel_diversity":   { "$ref": "#/$defs/DiversitySignal" },
                "conversation_depth":  { "$ref": "#/$defs/DepthSignal" },
                "follow_up_initiated": { "$ref": "#/$defs/BooleanSignal" }
              }
            },
            "behaviour": {
              "type": "object",
              "required": ["prior_customer", "referral_source", "content_engagement", "form_completion"],
              "additionalProperties": true,
              "properties": {
                "prior_customer":     { "$ref": "#/$defs/BooleanSignal" },
                "referral_source":    { "$ref": "#/$defs/ReferralSignal" },
                "content_engagement": { "$ref": "#/$defs/EngagementLevelSignal" },
                "form_completion":    { "$ref": "#/$defs/BooleanSignal" }
              }
            },
            "context": {
              "type": "object",
              "required": ["geography_tier", "account_growth_signal", "seasonal_relevance"],
              "additionalProperties": true,
              "properties": {
                "geography_tier":        { "$ref": "#/$defs/IntegerOrNotDetected" },
                "account_growth_signal": { "$ref": "#/$defs/BooleanSignal" },
                "seasonal_relevance":    { "$ref": "#/$defs/SeasonalSignal" }
              }
            }
          }
        }
      }
    },
    "context_inputs": {
      "type": "object",
      "description": "Prior scoring context. All fields null for variant=new. See VARIANT_* cross-field rules.",
      "additionalProperties": false,
      "properties": {
        "prior_score":    { "type": ["integer", "null"], "minimum": 0, "maximum": 100 },
        "prior_bucket":   { "type": ["string", "null"], "enum": ["hot", "warm", "cold", null] },
        "feedback_reason": { "type": ["string", "null"], "minLength": 5, "maxLength": 500 }
      }
    }
  },
  "$defs": {
    "BooleanSignal":         { "oneOf": [{ "type": "boolean" }, { "type": "string", "const": "not_detected" }] },
    "BooleanOrPartialSignal": { "oneOf": [{ "type": "boolean" }, { "type": "string", "enum": ["partial", "not_detected"] }] },
    "BooleanSignalWithNote": {
      "oneOf": [
        { "type": "boolean" },
        { "type": "string", "const": "not_detected" },
        { "type": "object", "required": ["value", "note"], "additionalProperties": false,
          "properties": { "value": { "type": "boolean" }, "note": { "type": "string", "minLength": 1, "maxLength": 200 } } }
      ]
    },
    "SpeedSignal":           { "type": "string", "enum": ["fast", "medium", "slow", "not_detected"] },
    "IntegerOrNotDetected":  { "oneOf": [{ "type": "integer", "minimum": 0 }, { "type": "string", "const": "not_detected" }] },
    "DiversitySignal":       { "type": "string", "enum": ["single", "multi", "not_detected"] },
    "DepthSignal":           { "type": "string", "enum": ["low", "medium", "high", "not_detected"] },
    "ReferralSignal":        { "type": "string", "enum": ["referred", "direct", "organic", "not_detected"] },
    "EngagementLevelSignal": { "type": "string", "enum": ["none", "low", "medium", "high", "not_detected"] },
    "SeasonalSignal":        { "type": "string", "enum": ["favourable", "neutral", "unfavourable", "not_detected"] }
  }
}
```

---

## OUTPUT_SCHEMA

The 7 fields the LLM returns. The Output Schema Layer adds `schema_version`, `prompt_version`, and `model` after validation — the LLM never writes those fields.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "LLMOutputContract",
  "description": "Structured output returned by the Rating Agent LLM call.",
  "type": "object",
  "required": ["score", "bucket", "reasoning", "lead_completeness", "sub_scores", "recommended_action", "needs_review"],
  "additionalProperties": false,
  "properties": {
    "score": { "type": "integer", "minimum": 0, "maximum": 100 },
    "bucket": { "type": "string", "enum": ["hot", "warm", "cold"] },
    "reasoning": {
      "type": "object",
      "required": ["primary_driver", "signal_contributors", "data_gaps", "salesperson_note"],
      "additionalProperties": false,
      "description": "Structured reasoning object. The prompt OUTPUT FORMAT section must instruct the LLM to return this exact structure.",
      "properties": {
        "primary_driver": {
          "type": "string", "minLength": 10, "maxLength": 200,
          "description": "One sentence naming the dominant factor(s) that drove the score."
        },
        "signal_contributors": {
          "type": "array", "minItems": 1, "maxItems": 10,
          "description": "The 1–10 most significant signals, positive and negative.",
          "items": {
            "type": "object",
            "required": ["signal", "dimension", "direction", "weight"],
            "additionalProperties": false,
            "properties": {
              "signal":    { "type": "string", "minLength": 1 },
              "dimension": { "type": "string", "enum": ["fit", "intent", "engagement", "behaviour", "context"] },
              "direction": { "type": "string", "enum": ["positive", "negative"] },
              "weight":    { "type": "string", "enum": ["high", "medium", "low"] }
            }
          }
        },
        "data_gaps": {
          "type": "array",
          "description": "Signal names or field names that were not_detected and meaningfully limited the score. Empty array if no significant gaps.",
          "items": { "type": "string", "minLength": 1 }
        },
        "salesperson_note": {
          "type": "string", "minLength": 10, "maxLength": 300,
          "description": "Plain-language note written for the salesperson explaining why this lead has this score and what to do."
        }
      }
    },
    "lead_completeness": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "sub_scores": {
      "type": "object",
      "required": ["fit", "intent", "engagement", "behaviour", "context"],
      "additionalProperties": false,
      "properties": {
        "fit":        { "type": "integer", "minimum": 0, "maximum": 25 },
        "intent":     { "type": "integer", "minimum": 0, "maximum": 25 },
        "engagement": { "type": "integer", "minimum": 0, "maximum": 20 },
        "behaviour":  { "type": "integer", "minimum": 0, "maximum": 20 },
        "context":    { "type": "integer", "minimum": 0, "maximum": 10 }
      }
    },
    "recommended_action": {
      "type": "string",
      "enum": ["call_immediately", "schedule_demo", "send_pricing_deck", "follow_up_scheduled", "send_qualifying_message", "nurture", "archive"],
      "description": "The prompt OUTPUT FORMAT section must list these 7 values explicitly."
    },
    "needs_review": {
      "type": "boolean", "const": false,
      "description": "LLM always returns false. The Output Schema Layer sets this to true when lead_completeness < threshold."
    }
  }
}
```

---

## VALIDATION_RULES

```json
{
  "$id": "ValidationRules",
  "version": "1.1.0",
  "input_rules": {
    "cross_field_rules": [
      {
        "rule_id": "WEIGHT_SUM",
        "description": "persona.scoring_weights.fit + intent + engagement + behaviour + context must equal 1.0",
        "tolerance": 0.001,
        "failure_action": "PersonaInvalidError — halt, do not call LLM, alert admin"
      },
      {
        "rule_id": "THRESHOLD_ORDER",
        "description": "persona.warm_min must be strictly less than persona.hot_min",
        "failure_action": "PersonaInvalidError — halt, do not call LLM, alert admin"
      },
      {
        "rule_id": "VARIANT_NEW",
        "description": "When variant = 'new': all context_inputs fields must be null; behavior.touchpoints must be absent or []",
        "failure_action": "InputValidationError — reject, do not call LLM"
      },
      {
        "rule_id": "VARIANT_RETURNING",
        "description": "When variant = 'returning': context_inputs.prior_score and prior_bucket must be non-null; behavior.touchpoints must be non-empty",
        "failure_action": "InputValidationError — reject, do not call LLM"
      },
      {
        "rule_id": "VARIANT_RESCORE",
        "description": "When variant = 'rescore': context_inputs.feedback_reason must be a non-null string; context_inputs.prior_score and prior_bucket must be non-null",
        "failure_action": "InputValidationError — reject, do not call LLM"
      },
      {
        "rule_id": "SIGNAL_ALL_PRESENT",
        "description": "Every signal key in the tenant's signal registry must appear in derived_metrics.signal_values under its dimension. Use 'not_detected' for unevaluated signals — absence is not permitted.",
        "failure_action": "PromptAssemblyError — reject, do not call LLM"
      },
      {
        "rule_id": "COMPANY_B2B_REQUIRED",
        "description": "When persona.business_type = 'B2B': company.name, company.industry, and company.role must all be non-null. Use 'not_detected' string if unknown, but null is not permitted.",
        "failure_action": "InputValidationError — log warning and proceed (not a hard stop; enrichment may have failed). Lead completeness is reduced automatically."
      }
    ]
  },
  "output_rules": {
    "cross_field_rules": [
      {
        "rule_id": "SUB_SCORES_SUM",
        "description": "sub_scores.fit + intent + engagement + behaviour + context must equal score",
        "tolerance": 1,
        "failure_action": "OutputValidationError — retry with schema correction message"
      },
      {
        "rule_id": "BUCKET_SCORE_CONSISTENCY",
        "description": "bucket must be consistent with score and tenant banding thresholds: hot if score >= hot_min; warm if score >= warm_min and < hot_min; cold if score < warm_min. On mismatch: threshold-derived bucket wins; discrepancy is logged.",
        "failure_action": "Override bucket to threshold-derived value; log discrepancy to lineage_record; do not retry"
      },
      {
        "rule_id": "COMPLETENESS_ECHO",
        "description": "lead_completeness in output must equal lead_completeness in input (derived_metrics.lead_completeness). Tolerance: 0.001.",
        "failure_action": "OutputValidationError — retry with schema correction message"
      },
      {
        "rule_id": "NEEDS_REVIEW_CONST",
        "description": "LLM must return needs_review = false. The Output Schema Layer sets it to true when lead_completeness < threshold.",
        "failure_action": "OutputValidationError — retry with schema correction message"
      }
    ]
  },
  "malformed_json_conditions": [
    "Response is not parseable as JSON",
    "Response contains text before or after the JSON object",
    "Response is a JSON array rather than object",
    "Response is a markdown code block wrapping JSON",
    "Any required field is absent",
    "Any field has the wrong JSON type",
    "Any enum field contains a value not in the defined enum list",
    "Any numeric field is outside its defined range",
    "Any cross-field rule violated beyond its defined tolerance"
  ],
  "retry_policy": {
    "max_attempts": 2,
    "attempt_1": { "description": "Original LLM call", "timeout_seconds": 30 },
    "attempt_2": {
      "description": "Retry with schema correction appended to user message",
      "timeout_seconds": 45,
      "correction_message_template": "Your previous response failed validation. Reason: {validation_failure_reason}. Return a single valid JSON object exactly matching the schema. No other text."
    },
    "retry_triggers": ["malformed_json", "schema_mismatch", "llm_timeout", "transient_provider_error_5xx"],
    "no_retry_triggers": ["auth_failure", "bad_request_4xx_non_timeout", "PersonaInvalidError", "PersonaNotFoundError", "InputValidationError"]
  },
  "fallback_behavior": {
    "trigger": "Two consecutive failures (any combination of retry_triggers)",
    "action": "Return ScoringFailure",
    "scoring_failure_schema": {
      "failure_reason": { "type": "string", "enum": ["timeout", "malformed_output", "rate_limit_exhausted", "schema_mismatch", "provider_error"] },
      "retry_count":    { "type": "integer", "minimum": 0, "maximum": 2 },
      "lead_id":        { "type": "string", "format": "uuid" },
      "prompt_version": { "type": "string", "pattern": "^v\\d+\\.\\d+\\.\\d+$" },
      "timestamp":      { "type": "string", "format": "date-time" }
    },
    "orchestrator_action": { "pipeline_stage": "human_review", "reason": "scoring_failed" }
  },
  "output_schema_layer_augmentation": {
    "description": "After LLM output passes validation, the Output Schema Layer adds three fields. The LLM never writes these.",
    "fields_added": {
      "schema_version": { "type": "string", "source": "system constant from active ScoringOutput schema definition" },
      "prompt_version": { "type": "string", "source": "input.prompt_template_version passed through from LLM call context" },
      "model":          { "type": "string", "source": "LLM provider API response metadata", "example": "claude-sonnet-4-6" }
    },
    "additional_checks": [
      "banding_enforcement: if LLM bucket disagrees with score + thresholds, threshold-derived bucket wins; log discrepancy",
      "needs_review_gate: if lead_completeness < configured threshold, override needs_review to true and route to human_review queue",
      "schema_validation: all fields type-checked and coerced (bucket lowercased, score rounded to integer)"
    ]
  }
}
```

---

## Tenant-Configurable Signal Extension

The signal_values section above reflects Gamoft's default signal set. Other tenants define their own signals via the Persona Agent (Step 3).

**How extension works:**
- Signal dimensions (fit, intent, engagement, behaviour, context) are fixed — tenants may not add new dimensions
- Signal keys within each dimension are tenant-defined — tenants may define any number of signals per dimension, with any name
- The `additionalProperties: true` on each dimension object in the schema allows tenant-specific keys to pass validation
- The `SIGNAL_ALL_PRESENT` cross-field rule enforces that every signal in the tenant's registry is present in the input — the base schema properties are the minimum floor

**Validation approach:** Base schema validation runs first (catches type errors on known fields). Then `SIGNAL_ALL_PRESENT` runs against the tenant's signal registry (catches missing tenant-specific signals). Both must pass.

---

## Open Decisions

| Decision | Status |
|---|---|
| `needs_review` threshold: 0.60 or 0.75 | TBD — team decision after Month 1 data |
| `recommended_action` enum extension per tenant | TBD — global 7-value enum vs per-tenant extensions via PersonaObject |
| Message Parser (Haiku) I/O contract | Deferred — Rating Agent contract takes priority; Message Parser contract to be written before DM path goes to production |
| COMPANY_B2B_REQUIRED rule severity | Currently a warning (not hard stop) — may be elevated to hard stop after Phase 0 data reveals how often B2B enrichment fails |
