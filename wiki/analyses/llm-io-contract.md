---
type: analysis
question: "What are the strict, machine-consumable LLM input and output JSON contracts for the Rating Agent, including schema validation rules?"
date: 2026-05-05
tags: [rating-agent, scoring, schema, validation, json-contract, input-contract, output-contract, pipeline-1]
sources_consulted:
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/prompt-template-framework]]"
  - "[[concepts/signal-types]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/confidence-first-class]]"
  - "[[analyses/orchestration-layer-spec]]"
status: COMPLETE
---

# LLM I/O Contract — Rating Agent

**Question:** What are the strict, machine-consumable LLM input and output JSON contracts for the Rating Agent?
**Date:** 2026-05-05

---

## Answer / Finding

Three machine-consumable contracts are defined below. All three are pure JSON (no comments). They plug directly into an automated pipeline without human correction.

- **INPUT_SCHEMA** — the full structured input passed to the Rating Agent LLM call
- **OUTPUT_SCHEMA** — the 7 fields the LLM returns (before Output Schema Layer augmentation)
- **VALIDATION_RULES** — type, range, enum, cross-field, retry, and fallback rules

**Design decisions made here that are stricter than the current vault spec:**

| Field | Current vault | This contract | Reason |
|---|---|---|---|
| `reasoning` | freeform string | structured object (4 sub-fields) | Enables machine parsing without regex; eliminates freeform blob ambiguity |
| `recommended_action` | one-sentence string | enum of 7 values | Deterministic parsing; eliminates LLM hallucination of novel action verbs |
| Signal value types | described in prose | discriminated union per signal class | Prevents type confusion between `false` (detected, negative) and `"not_detected"` (not evaluated) |
| `confidence` (task term) | `lead_completeness` (vault term) | `lead_completeness` — vault name wins | Vault RESOLVED 2026-04-22: this is data completeness, not LLM self-confidence |

---

## INPUT_SCHEMA

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LLMInputContract",
  "version": "1.0.0",
  "type": "object",
  "required": [
    "schema_version",
    "tenant_id",
    "lead_id",
    "variant",
    "prompt_template_version",
    "lead",
    "company",
    "persona",
    "behavior",
    "derived_metrics",
    "context_inputs"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^v\\d+\\.\\d+$"
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
        "name": {
          "type": ["string", "null"],
          "minLength": 1
        },
        "phone": {
          "type": "string",
          "pattern": "^\\+[1-9]\\d{6,14}$"
        },
        "email": {
          "type": ["string", "null"],
          "format": "email"
        },
        "channel": {
          "type": "string",
          "enum": [
            "whatsapp",
            "instagram_dm",
            "facebook_dm",
            "lead_ad",
            "website_form",
            "linkedin"
          ]
        },
        "source": {
          "type": "string",
          "minLength": 1
        },
        "first_contact_date": {
          "type": "string",
          "format": "date"
        },
        "geography": {
          "type": ["string", "null"]
        },
        "city_tier": {
          "type": ["integer", "null"],
          "minimum": 1,
          "maximum": 3
        }
      }
    },
    "company": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": ["string", "null"],
          "minLength": 1
        },
        "industry": {
          "type": ["string", "null"],
          "minLength": 2
        },
        "size_employees": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "role": {
          "type": ["string", "null"],
          "minLength": 1
        },
        "registration_id": {
          "type": ["string", "null"]
        }
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
        "tenant_name": {
          "type": "string",
          "minLength": 1
        },
        "business_type": {
          "type": "string",
          "enum": ["B2B", "B2C"]
        },
        "icp_summary": {
          "type": "string",
          "minLength": 20,
          "maxLength": 2000
        },
        "disqualifying_profiles": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 5
          },
          "minItems": 1
        },
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
        "hot_min": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "warm_min": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "persona_version": {
          "type": "string",
          "pattern": "^v\\d+\\.\\d+\\.\\d+$"
        }
      }
    },
    "behavior": {
      "type": "object",
      "required": [
        "revisit_count",
        "channel_diversity",
        "conversation_depth",
        "follow_up_initiated"
      ],
      "additionalProperties": false,
      "properties": {
        "revisit_count": {
          "type": "integer",
          "minimum": 1
        },
        "channel_diversity": {
          "type": "string",
          "enum": ["single", "multi"]
        },
        "conversation_depth": {
          "type": "string",
          "enum": ["low", "medium", "high"]
        },
        "follow_up_initiated": {
          "type": "boolean"
        },
        "response_speed": {
          "type": ["string", "null"],
          "enum": ["fast", "medium", "slow", null]
        },
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
        "lead_completeness": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0
        },
        "signal_values": {
          "type": "object",
          "required": ["fit", "intent", "engagement", "behaviour", "context"],
          "additionalProperties": false,
          "properties": {
            "fit": {
              "type": "object",
              "required": ["industry_match", "role_relevance", "company_size_fit", "serviceability"],
              "additionalProperties": false,
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
              "additionalProperties": false,
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
              "additionalProperties": false,
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
              "additionalProperties": false,
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
              "additionalProperties": false,
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
      "required": ["prior_score", "prior_bucket", "feedback_reason"],
      "additionalProperties": false,
      "properties": {
        "prior_score": {
          "type": ["integer", "null"],
          "minimum": 0,
          "maximum": 100
        },
        "prior_bucket": {
          "type": ["string", "null"],
          "enum": ["hot", "warm", "cold", null]
        },
        "feedback_reason": {
          "type": ["string", "null"],
          "minLength": 5,
          "maxLength": 500
        }
      }
    }
  },
  "$defs": {
    "BooleanSignal": {
      "oneOf": [
        { "type": "boolean" },
        { "type": "string", "const": "not_detected" }
      ]
    },
    "BooleanOrPartialSignal": {
      "oneOf": [
        { "type": "boolean" },
        { "type": "string", "enum": ["partial", "not_detected"] }
      ]
    },
    "BooleanSignalWithNote": {
      "oneOf": [
        { "type": "boolean" },
        { "type": "string", "const": "not_detected" },
        {
          "type": "object",
          "required": ["value", "note"],
          "additionalProperties": false,
          "properties": {
            "value": { "type": "boolean" },
            "note":  { "type": "string", "minLength": 1, "maxLength": 200 }
          }
        }
      ]
    },
    "SpeedSignal": {
      "type": "string",
      "enum": ["fast", "medium", "slow", "not_detected"]
    },
    "IntegerOrNotDetected": {
      "oneOf": [
        { "type": "integer", "minimum": 0 },
        { "type": "string", "const": "not_detected" }
      ]
    },
    "DiversitySignal": {
      "type": "string",
      "enum": ["single", "multi", "not_detected"]
    },
    "DepthSignal": {
      "type": "string",
      "enum": ["low", "medium", "high", "not_detected"]
    },
    "ReferralSignal": {
      "type": "string",
      "enum": ["referred", "direct", "organic", "not_detected"]
    },
    "EngagementLevelSignal": {
      "type": "string",
      "enum": ["none", "low", "medium", "high", "not_detected"]
    },
    "SeasonalSignal": {
      "type": "string",
      "enum": ["favourable", "neutral", "unfavourable", "not_detected"]
    }
  }
}
```

---

## OUTPUT_SCHEMA

This schema defines the 7 fields the LLM itself must return. The Output Schema Layer adds `schema_version`, `prompt_version`, and `model` after validation — the LLM never writes those fields.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LLMOutputContract",
  "version": "1.0.0",
  "type": "object",
  "required": [
    "score",
    "bucket",
    "reasoning",
    "lead_completeness",
    "sub_scores",
    "recommended_action",
    "needs_review"
  ],
  "additionalProperties": false,
  "properties": {
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100
    },
    "bucket": {
      "type": "string",
      "enum": ["hot", "warm", "cold"]
    },
    "reasoning": {
      "type": "object",
      "required": [
        "primary_driver",
        "signal_contributors",
        "data_gaps",
        "salesperson_note"
      ],
      "additionalProperties": false,
      "properties": {
        "primary_driver": {
          "type": "string",
          "minLength": 10,
          "maxLength": 200
        },
        "signal_contributors": {
          "type": "array",
          "minItems": 1,
          "maxItems": 10,
          "items": {
            "type": "object",
            "required": ["signal", "dimension", "direction", "weight"],
            "additionalProperties": false,
            "properties": {
              "signal": {
                "type": "string",
                "minLength": 1
              },
              "dimension": {
                "type": "string",
                "enum": ["fit", "intent", "engagement", "behaviour", "context"]
              },
              "direction": {
                "type": "string",
                "enum": ["positive", "negative"]
              },
              "weight": {
                "type": "string",
                "enum": ["high", "medium", "low"]
              }
            }
          }
        },
        "data_gaps": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "salesperson_note": {
          "type": "string",
          "minLength": 10,
          "maxLength": 300
        }
      }
    },
    "lead_completeness": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
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
      "enum": [
        "call_immediately",
        "schedule_demo",
        "send_pricing_deck",
        "follow_up_scheduled",
        "send_qualifying_message",
        "nurture",
        "archive"
      ]
    },
    "needs_review": {
      "type": "boolean",
      "const": false
    }
  }
}
```

---

## VALIDATION_RULES

```json
{
  "schema": "ValidationRules",
  "version": "1.0.0",
  "input_rules": {
    "required_fields": {
      "top_level": [
        "schema_version",
        "tenant_id",
        "lead_id",
        "variant",
        "prompt_template_version",
        "lead",
        "company",
        "persona",
        "behavior",
        "derived_metrics",
        "context_inputs"
      ],
      "lead": ["phone", "channel", "source", "first_contact_date"],
      "persona": [
        "tenant_name",
        "business_type",
        "icp_summary",
        "disqualifying_profiles",
        "scoring_weights",
        "hot_min",
        "warm_min",
        "persona_version"
      ],
      "persona.scoring_weights": ["fit", "intent", "engagement", "behaviour", "context"],
      "behavior": ["revisit_count", "channel_diversity", "conversation_depth", "follow_up_initiated"],
      "derived_metrics": ["lead_completeness", "signal_values"],
      "derived_metrics.signal_values": ["fit", "intent", "engagement", "behaviour", "context"],
      "context_inputs": ["prior_score", "prior_bucket", "feedback_reason"]
    },
    "type_rules": {
      "schema_version":               "string matching ^v\\d+\\.\\d+$",
      "tenant_id":                    "string uuid format",
      "lead_id":                      "string uuid format",
      "variant":                      "string enum",
      "prompt_template_version":      "string matching ^v\\d+\\.\\d+\\.\\d+$",
      "lead.phone":                   "string E.164 format ^\\+[1-9]\\d{6,14}$",
      "lead.email":                   "string email format or null",
      "lead.city_tier":               "integer 1-3 or null",
      "lead.first_contact_date":      "string ISO 8601 date YYYY-MM-DD",
      "company.size_employees":       "integer >= 1 or null",
      "persona.hot_min":              "integer",
      "persona.warm_min":             "integer",
      "persona.scoring_weights.*":    "number 0.0 to 1.0",
      "behavior.revisit_count":       "integer >= 1",
      "derived_metrics.lead_completeness": "number 0.0 to 1.0",
      "context_inputs.prior_score":   "integer 0-100 or null",
      "context_inputs.prior_bucket":  "string enum or null",
      "context_inputs.feedback_reason": "string 5-500 chars or null"
    },
    "range_rules": {
      "lead.city_tier":                { "minimum": 1, "maximum": 3, "nullable": true },
      "company.size_employees":        { "minimum": 1, "nullable": true },
      "persona.hot_min":               { "minimum": 1, "maximum": 100 },
      "persona.warm_min":              { "minimum": 1, "maximum": 100 },
      "persona.scoring_weights.*":     { "minimum": 0.0, "maximum": 1.0 },
      "behavior.revisit_count":        { "minimum": 1 },
      "derived_metrics.lead_completeness": { "minimum": 0.0, "maximum": 1.0 },
      "context_inputs.prior_score":    { "minimum": 0, "maximum": 100, "nullable": true }
    },
    "enum_rules": {
      "variant":                 ["new", "returning", "rescore"],
      "lead.channel":            ["whatsapp", "instagram_dm", "facebook_dm", "lead_ad", "website_form", "linkedin"],
      "persona.business_type":   ["B2B", "B2C"],
      "behavior.channel_diversity":   ["single", "multi"],
      "behavior.conversation_depth":  ["low", "medium", "high"],
      "behavior.response_speed":      ["fast", "medium", "slow", null],
      "behavior.touchpoints[].channel":   ["whatsapp", "instagram_dm", "facebook_dm", "email", "call", "website"],
      "behavior.touchpoints[].direction": ["inbound", "outbound"],
      "context_inputs.prior_bucket":  ["hot", "warm", "cold", null],
      "signal_value_types": {
        "BooleanSignal":          "true | false | \"not_detected\"",
        "BooleanOrPartialSignal": "true | false | \"partial\" | \"not_detected\"",
        "SpeedSignal":            "\"fast\" | \"medium\" | \"slow\" | \"not_detected\"",
        "DiversitySignal":        "\"single\" | \"multi\" | \"not_detected\"",
        "DepthSignal":            "\"low\" | \"medium\" | \"high\" | \"not_detected\"",
        "ReferralSignal":         "\"referred\" | \"direct\" | \"organic\" | \"not_detected\"",
        "EngagementLevelSignal":  "\"none\" | \"low\" | \"medium\" | \"high\" | \"not_detected\"",
        "SeasonalSignal":         "\"favourable\" | \"neutral\" | \"unfavourable\" | \"not_detected\"",
        "IntegerOrNotDetected":   "integer >= 0 | \"not_detected\""
      }
    },
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
        "rule_id": "VARIANT_NEW_NULLS",
        "description": "When variant = 'new': context_inputs.prior_score, prior_bucket, feedback_reason must all be null; behavior.touchpoints must be []",
        "failure_action": "InputValidationError — reject, do not call LLM"
      },
      {
        "rule_id": "VARIANT_RETURNING_TOUCHPOINTS",
        "description": "When variant = 'returning': behavior.touchpoints must be non-empty array (minItems: 1); context_inputs.prior_score and prior_bucket must be non-null",
        "failure_action": "InputValidationError — reject, do not call LLM"
      },
      {
        "rule_id": "VARIANT_RESCORE_FEEDBACK",
        "description": "When variant = 'rescore': context_inputs.feedback_reason must be a non-null string; context_inputs.prior_score and prior_bucket must be non-null",
        "failure_action": "InputValidationError — reject, do not call LLM"
      },
      {
        "rule_id": "SIGNAL_ALL_PRESENT",
        "description": "Every signal defined in the tenant's signal registry must appear in derived_metrics.signal_values. Missing signal keys are not permitted; use 'not_detected' for unevaluated signals.",
        "failure_action": "InputValidationError — reject, do not call LLM"
      }
    ]
  },
  "output_rules": {
    "required_fields": [
      "score",
      "bucket",
      "reasoning",
      "lead_completeness",
      "sub_scores",
      "recommended_action",
      "needs_review"
    ],
    "type_rules": {
      "score":              "integer",
      "bucket":             "string enum",
      "reasoning":          "object",
      "reasoning.primary_driver":           "string 10-200 chars",
      "reasoning.signal_contributors":      "array minItems 1 maxItems 10",
      "reasoning.signal_contributors[].signal":    "string",
      "reasoning.signal_contributors[].dimension": "string enum",
      "reasoning.signal_contributors[].direction": "string enum",
      "reasoning.signal_contributors[].weight":    "string enum",
      "reasoning.data_gaps":                "array of strings",
      "reasoning.salesperson_note":         "string 10-300 chars",
      "lead_completeness":  "number",
      "sub_scores":         "object",
      "sub_scores.fit":        "integer",
      "sub_scores.intent":     "integer",
      "sub_scores.engagement": "integer",
      "sub_scores.behaviour":  "integer",
      "sub_scores.context":    "integer",
      "recommended_action": "string enum",
      "needs_review":       "boolean"
    },
    "range_rules": {
      "score":                 { "minimum": 0, "maximum": 100 },
      "lead_completeness":     { "minimum": 0.0, "maximum": 1.0 },
      "sub_scores.fit":        { "minimum": 0, "maximum": 25 },
      "sub_scores.intent":     { "minimum": 0, "maximum": 25 },
      "sub_scores.engagement": { "minimum": 0, "maximum": 20 },
      "sub_scores.behaviour":  { "minimum": 0, "maximum": 20 },
      "sub_scores.context":    { "minimum": 0, "maximum": 10 }
    },
    "enum_rules": {
      "bucket":               ["hot", "warm", "cold"],
      "reasoning.signal_contributors[].dimension": ["fit", "intent", "engagement", "behaviour", "context"],
      "reasoning.signal_contributors[].direction": ["positive", "negative"],
      "reasoning.signal_contributors[].weight":    ["high", "medium", "low"],
      "recommended_action":   [
        "call_immediately",
        "schedule_demo",
        "send_pricing_deck",
        "follow_up_scheduled",
        "send_qualifying_message",
        "nurture",
        "archive"
      ],
      "needs_review":         [false]
    },
    "cross_field_rules": [
      {
        "rule_id": "SUB_SCORES_SUM",
        "description": "sub_scores.fit + intent + engagement + behaviour + context must equal score",
        "tolerance": 1,
        "failure_action": "OutputValidationError — retry with schema correction message"
      },
      {
        "rule_id": "BUCKET_SCORE_CONSISTENCY",
        "description": "bucket must be consistent with score and tenant banding thresholds: hot if score >= hot_min; warm if score >= warm_min and score < hot_min; cold if score < warm_min. On mismatch: threshold-derived bucket wins; discrepancy is logged.",
        "failure_action": "Override bucket to threshold-derived value; log discrepancy to lineage_record; do not retry"
      },
      {
        "rule_id": "COMPLETENESS_ECHO",
        "description": "lead_completeness in output must equal lead_completeness in input (derived_metrics.lead_completeness). Tolerance: 0.001.",
        "failure_action": "OutputValidationError — retry with schema correction message"
      },
      {
        "rule_id": "NEEDS_REVIEW_CONST",
        "description": "needs_review must be false. The Output Schema Layer sets needs_review to true when lead_completeness < configured threshold. The LLM never sets needs_review to true.",
        "failure_action": "OutputValidationError — retry with schema correction message"
      }
    ]
  },
  "malformed_json_definition": {
    "conditions": [
      "Response is not parseable as JSON (syntax error)",
      "Response contains text before or after the JSON object",
      "Response is a JSON array rather than a JSON object",
      "Response is a markdown code block wrapping JSON (```json ... ```) — the wrapper itself is malformed",
      "Any required field is absent from the parsed object",
      "Any field has the wrong JSON type (string where integer expected, array where object expected, etc.)",
      "Any enum field contains a value not in the defined enum list",
      "Any numeric field is outside its defined range",
      "Any cross-field rule is violated beyond its defined tolerance"
    ]
  },
  "retry_policy": {
    "max_attempts": 2,
    "attempt_1": {
      "description": "Original LLM call with standard prompt",
      "timeout_seconds": 30
    },
    "attempt_2": {
      "description": "Retry with schema correction message appended to user message. Correction message states the specific validation failure from attempt 1 and repeats the output format constraint.",
      "timeout_seconds": 45,
      "correction_message_template": "Your previous response failed validation. Reason: {validation_failure_reason}. Return a single valid JSON object exactly matching the schema. No other text."
    },
    "retry_triggers": [
      "malformed_json",
      "schema_mismatch",
      "llm_timeout",
      "transient_provider_error_5xx"
    ],
    "no_retry_triggers": [
      "auth_failure",
      "bad_request_4xx_non_timeout",
      "PersonaInvalidError",
      "PersonaNotFoundError",
      "InputValidationError"
    ]
  },
  "fallback_behavior": {
    "trigger": "Two consecutive failures (any combination of retry_triggers)",
    "action": "Return ScoringFailure",
    "scoring_failure_schema": {
      "failure_reason": {
        "type": "string",
        "enum": ["timeout", "malformed_output", "rate_limit_exhausted", "schema_mismatch", "provider_error"]
      },
      "retry_count": {
        "type": "integer",
        "minimum": 0,
        "maximum": 2
      },
      "lead_id": {
        "type": "string",
        "format": "uuid"
      },
      "prompt_version": {
        "type": "string",
        "pattern": "^v\\d+\\.\\d+\\.\\d+$"
      },
      "timestamp": {
        "type": "string",
        "format": "date-time"
      }
    },
    "orchestrator_action": {
      "pipeline_stage": "human_review",
      "reason": "scoring_failed"
    }
  },
  "output_schema_layer_augmentation": {
    "description": "After LLM output passes validation, the Output Schema Layer adds three fields before storing. These fields are never written by the LLM.",
    "fields_added": {
      "schema_version": {
        "type": "string",
        "pattern": "^v\\d+\\.\\d+$",
        "source": "system constant from active ScoringOutput schema definition"
      },
      "prompt_version": {
        "type": "string",
        "pattern": "^v\\d+\\.\\d+\\.\\d+$",
        "source": "input.prompt_template_version passed through from the LLM call context"
      },
      "model": {
        "type": "string",
        "source": "LLM provider API response metadata",
        "example": "claude-sonnet-4-6"
      }
    },
    "additional_checks": [
      "banding_enforcement: if LLM bucket disagrees with score+thresholds, threshold-derived bucket wins; log discrepancy",
      "needs_review_gate: if lead_completeness < configured threshold (0.60 or 0.75 — team decision pending), override needs_review to true and route to human_review queue",
      "schema_validation: all fields type-checked and coerced (bucket lowercased, score rounded to integer)"
    ]
  }
}
```

---

## Evidence

- Sub-scores schema (5 fields, locked 2026-05-03): [[analyses/rating-agent-spec]] Full ScoringOutput Schema
- Banding enforcement and needs_review gate logic: [[analyses/rating-agent-spec]] Component 4 — Output Schema Layer
- Signal values format and `not_detected` sentinel: [[analyses/prompt-template-framework]] Section 6 and 7 (samples)
- Retry policy (1 retry, schema reminder): [[analyses/rating-agent-spec]] Failure Handling table
- Variant-conditional inputs: [[analyses/rating-agent-spec]] Conditional Inputs section
- lead_completeness is NOT LLM confidence: [[concepts/confidence-first-class]]
- Five scoring dimensions and max scores: [[concepts/signal-types]]
- Output Schema Layer adds schema_version, prompt_version, model: [[analyses/prompt-template-framework]] Section 8
- ScoringFailure schema: [[analyses/rating-agent-spec]] Full ScoringOutput Schema
- Bucket thresholds default (80/55): [[analyses/orchestration-layer-spec]]

---

## Caveats & Gaps

- **`recommended_action` enum is hardened here.** The vault's current spec allows a freeform string. This contract defines 7 enumerated values. The prompt template's OUTPUT FORMAT section must be updated to list these 7 values explicitly — otherwise the LLM cannot produce a valid enum value.
- **`reasoning` is hardened to a structured object here.** The vault's current spec uses a freeform string. The prompt template's OUTPUT FORMAT section must be updated with the 4-sub-field structure (`primary_driver`, `signal_contributors`, `data_gaps`, `salesperson_note`). This is a breaking change to the current prompt template.
- **Signal registry is tenant-configurable.** The `derived_metrics.signal_values` schema shown here reflects the Gamoft tenant's default signals. Additional tenants may define additional signal keys via the Persona Agent. The `SIGNAL_ALL_PRESENT` cross-field rule enforces that all *tenant-specific* signals are present — the base schema above must be extended per tenant.
- **needs_review threshold is TBD.** The `needs_review_gate` in `output_schema_layer_augmentation` references a threshold value (0.60 or 0.75) that is a pending team decision. See [[analyses/rating-agent-spec]] Open Decisions.
- **Output Schema Layer augmentation fields** (`schema_version`, `prompt_version`, `model`) are documented in `VALIDATION_RULES.output_schema_layer_augmentation` but are not part of the LLM OUTPUT_SCHEMA — they are system-added post-validation.

---

## Follow-up Questions

- Should the `recommended_action` enum be extended per tenant via the PersonaObject, or is a global 7-value enum sufficient for all tenants?
- Should `reasoning.signal_contributors` enforce that all named signals exist in the tenant's signal registry, or is the dimension enum enough for validation?
- Once the needs_review threshold is confirmed, this document should be updated with the live value in `VALIDATION_RULES.output_schema_layer_augmentation`.
- Should a separate contract be defined for the Message Parser (Haiku) output, or is the Rating Agent contract sufficient for initial pipeline validation?
