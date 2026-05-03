---
type: concept
name: "Intelligence Layer"
aliases: ["scoring layer", "LLM layer", "rating pipeline"]
tags: [intelligence-layer, scoring, architecture, llm, design-spec]
source_count: 1
last_updated: 2026-04-22
confidence: high
---

# Intelligence Layer

## Definition

The Intelligence Layer is the reasoning core of the lead scoring system. Its single job: take an enriched lead record and a tenant's scoring configuration, and produce a validated scoring output — a score from 0 to 100, a bucket (Hot, Warm, or Cold), a one-line reasoning, structured sub-scores, and a lead completeness score.

It is one of three system layers, alongside the Data Layer (storage, schema, read/write APIs) and the Orchestration Layer (pipeline triggering, routing, retry, persistence). It is the **only layer that performs LLM-based reasoning.**

## Four Internal Components

The Intelligence Layer is itself a four-stage internal pipeline. The Orchestration Layer sees only the single entry point; it never reaches inside.

```
[Orchestration Layer]
        |
        | score_lead(tenant_id, lead, variant, ...)
        v
+-------------------------------------------------------+
|              INTELLIGENCE LAYER                       |
|                                                       |
|  Persona Engine                                       |
|      | persona object (15-min TTL cache)              |
|      v                                                |
|  Prompt Layer                                         |
|      | assembled messages array + metadata            |
|      v                                                |
|  Rating Agent                                         |
|      | raw LLM response + call metadata               |
|      v                                                |
|  Output Schema Layer                                  |
|      | ScoringOutput | ScoringFailure                 |
+-------------------------------------------------------+
        |
        v
[Orchestration Layer] — persists result to Data Layer
```

### 1. Persona Engine

Builds the tenant-specific PersonaObject from the tenant's stored configuration. This object tells the scoring agent who the client is, what a good lead looks like, and how to weight the scoring dimensions.

- Loads tenant config on demand; caches assembled PersonaObjects in memory with a **15-minute TTL**.
- Cache invalidated when a tenant updates their scoring rubric.
- Fails fast if required config fields are missing — an incomplete persona is never passed downstream.
- Reads tenant config directly from the Data Layer (the only direct Data Layer read in the Intelligence Layer).

**Interface:** `get_persona(tenant_id: str) → PersonaObject`

**Failure modes:** `PersonaNotFoundError` (missing config), `PersonaInvalidError` (weights don't sum to 100).

### 2. Prompt Layer

Assembles the exact prompt sent to the LLM. Infrastructure, not an agent — holds templates, injects variables, selects the correct template variant.

- **Three variants:** `new` (new lead), `returning` (repeat lead with history), `rescore` (re-evaluation after feedback).
- Scoring rubric lives in the **system prompt** (static per tenant, LLM-provider-cacheable). Lead data lives in the **user prompt** (per-lead variable).
- Templates are versioned — every score record stores the prompt version used. Enables rollback and audit.
- Emits a pre-flight token count estimate; Rating Agent aborts early if the prompt exceeds the model's context window.

**Interface:** `assemble_prompt(persona, lead, variant, ...) → PromptBundle`

**Failure modes:** `PromptAssemblyError` (missing required lead field), `PromptTooLargeError` (token limit exceeded), `PromptVariantError` (unknown variant — bug in caller).

### 3. Rating Agent

Executes the single LLM call. Owns everything related to the model provider: authentication, timeouts, retries, rate limit handling, raw response parsing.

- Makes **exactly one logical LLM call** per scoring request. Physical retries on transient errors don't count as additional logical calls.
- Requests structured JSON output to reduce parsing fragility.
- **Hard timeout: 30 seconds** (LLM call budget within the 60-second layer timeout).
- Handles provider failures with exponential backoff: rate limits, 5xx, network timeouts. Non-retryable errors (auth, bad request) fail immediately.
- **Provider-agnostic interface** — the rest of the Intelligence Layer does not know which provider served the request.

**Interface:** `run_rating(prompt: PromptBundle, config: ModelConfig) → RatingResult`

**Failure modes:** `RatingTimeoutError`, `RatingRateLimitError`, `RatingAuthError`.

**Provider — RESOLVED 2026-05-03:** Anthropic Claude Sonnet 4.6 (primary). OpenAI GPT-4o via LiteLLM as fallback only. See [[analyses/tech-stack-research]].

### 4. Output Schema Layer

Turns the non-deterministic LLM output into a guaranteed, typed ScoringOutput. The contract between LLM reasoning and the rest of the system.

- Validates parsed JSON against the canonical scoring schema.
- Coerces minor inconsistencies: case normalisation, score rounding, whitespace trimming.
- **Banding rules always win over the LLM's bucket.** If the LLM's bucket disagrees with the score + tenant banding rules, banding wins and the discrepancy is logged.
- Applies the **lead completeness gate**: if lead completeness is below the configured threshold, sets `needs_review = true`. This is a success path — the score is stored and the lead is queued for review, not discarded.
- Handles schema evolution — records schema version on every output.
- On unrecoverable parsing failures, returns a typed ScoringFailure (never a malformed success).

**Interface:** `validate_output(rating, persona) → ScoringOutput | ScoringFailure`

## Public Interface

The Orchestration Layer calls the Intelligence Layer through one function only:

```python
score_lead(
    tenant_id: str,
    lead: EnrichedLead,
    variant: 'new' | 'returning' | 'rescore',
    existing: Optional[LeadRecord] = None,
    touchpoints: Optional[list[Touchpoint]] = None
) -> ScoringOutput | ScoringFailure
```

**Contracts:**
- Synchronous. Returns when scoring is complete.
- **Hard timeout: 60 seconds** (within the 90-second end-to-end budget).
- Never raises — always returns either ScoringOutput or ScoringFailure.
- Idempotent: same inputs → equivalent outputs (modulo LLM non-determinism smoothed by structured output mode).

## ScoringOutput Schema

```python
ScoringOutput {
    score: int                    # 0–100
    bucket: 'hot' | 'warm' | 'cold'
    reasoning: str                # one line
    lead_completeness: float      # 0.0–1.0  [NOT LLM confidence — see Tensions]
    sub_scores: {fit, intent, engagement, behaviour, context}
    recommended_action: str
    needs_review: bool            # true if completeness below threshold
    schema_version: str
    prompt_version: str
    model: str
}
```

## Design Principles

1. **Sonnet call per lead (all paths).** Rating Agent makes exactly one Sonnet call. On the DM path, a separate Message Parser (Haiku) fires upstream of this layer — see [[concepts/agent-vs-tool-classification]].
2. **Tenant-aware by configuration, not by code.** Behavioural differences come from the PersonaObject, never from branching logic.
3. **Deterministic contracts, non-deterministic core.** Output Schema Layer guarantees typed results despite LLM variability.
4. **Fail loudly, degrade gracefully.** All failure modes return typed errors — no silent corruption.
5. **No direct data layer writes.** Persistence stays with the Orchestration Layer.

## Observability Signals Emitted

Every scoring call emits: `prompt_version`, `template_id`, `model`, `provider`, `tokens_in`, `tokens_out`, `latency_ms` (end-to-end and per-phase), `retry_count`, `needs_review`, `schema_validation_result` (`pass` / `coerced` / `failed`).

## Boundaries — What This Layer Does NOT Do

- Store raw, enriched, or scored lead data (Data Layer).
- Decide when a lead should be scored or re-scored (Orchestration Layer).
- Fetch data from WhatsApp, Instagram, CRM, or any external source (Orchestration Layer).
- Normalise or deduplicate raw lead events (Orchestration Layer).
- Deliver notifications or generate output documents (Orchestration Layer).
- Manage tenant authentication, billing, or onboarding UI (out of system scope).

## Why It Matters

Isolating LLM reasoning in its own layer means prompt changes, model choices, and scoring logic can evolve independently of data storage and pipeline triggering. A prompt change never requires a database migration; a new data source never requires rewriting the scoring agent.

## Tensions & Contradictions

- **"Confidence" field in the design doc is a lead completeness score in practice.** The design document uses the term "confidence" for an LLM output field and routes leads to human review when it is low. The team has decided this field is **not LLM self-assessed confidence** (LLMs are poorly calibrated) but a **lead completeness score** — how complete the enriched lead data is. The routing logic (`needs_review` flag, threshold gate) still applies, but the input changes. This supersedes the `confidence` terminology throughout the design spec. See [[concepts/confidence-first-class]].
- **Open: lead completeness threshold.** The design doc proposed 0.6 or 0.75. Applies equally to a completeness threshold. Not yet locked.

## Open Decisions

| # | Decision | Options |
|---|---|---|
| 1 | Primary LLM provider | **RESOLVED 2026-05-03** — Anthropic Claude Sonnet 4.6 primary; OpenAI GPT-4o via LiteLLM fallback |
| 2 | Model config scope | Global (one model all tenants) or per-tenant override |
| 3 | Prompt storage | In code (git-versioned) or in data layer (editable without deployment) |
| 4 | Custom rules format | Free-text rules interpreted by LLM, or structured rules executed pre-LLM |
| 5 | Bucket disagreement handling | Log only, or surface as dashboard alert |
| 6 | Lead completeness threshold | Start at 0.6 (lenient) or 0.75 (conservative) |
| 7 | Sub-scores required? | Always required, or can LLM omit when lead data is thin? |

## Related Concepts

- [[concepts/signal-types]] — the five scoring dimensions the LLM reasons over; default weights defined here
- [[concepts/persona-layer]] — PersonaObject is the configuration bundle built by the Persona Engine
- [[concepts/confidence-first-class]] — routing and needs_review logic; corrected to lead completeness score
- [[concepts/lead-pipeline-architecture]] — the Intelligence Layer is the scoring step in Pipeline 1
- [[concepts/lineage-log]] — observability signals from the Intelligence Layer feed the governance lineage system
- [[concepts/data-entity-model]] — `lead_score`, `score_model_version`, `signal`, `signal_evaluation` are the data entities backing the Intelligence Layer's outputs

## Sources

- [[sources/2026-intelligence-layer-design]] — full design specification
