---
type: analysis
question: "What are the inputs, score output, reasoning output, and completeness output for the Rating Agent?"
date: 2026-04-26
tags: [agents, rating-agent, pipeline-1, scoring, specification, minimal-agent-set]
sources_consulted:
  - "[[concepts/intelligence-layer]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[concepts/signal-types]]"
  - "[[concepts/persona-layer]]"
  - "[[concepts/confidence-first-class]]"
  - "[[concepts/agent-vs-tool-classification]]"
status: COMPLETE
---

# Rating Agent — Specification

**Role in minimal agent set:** One of two agents in the system. Runs once per lead in Pipeline 1. Receives the tenant's scoring configuration (built by the Persona Agent) and an enriched, normalised lead record with pre-extracted signal values, and returns a validated, typed scoring output. This is the only LLM call per lead.

---

## Naming Clarification — Rating Agent (this document) vs Internal Rating Agent Component

Two things share similar names. They are at different levels of abstraction.

| Name | What it is | Level |
|---|---|---|
| **Rating Agent** *(this document)* | The full scoring step the orchestrator calls — `score_lead()`. Encompasses four internal components. The complete black box from the orchestrator's perspective. | Pipeline level |
| **Rating Agent (internal)** | Component 3 of the Intelligence Layer — the specific sub-component that makes the LLM call. One of four components inside `score_lead()`. | Intelligence Layer internal |

When this document says "Rating Agent", it means the full `score_lead()` call. The four internal components (Persona Engine, Prompt Layer, Rating Agent component, Output Schema Layer) are implementation detail.

---

## What the Rating Agent Does

The Rating Agent takes one enriched, normalised lead and returns a validated score. Internally it:
1. Loads and caches the tenant's scoring configuration (Persona Engine)
2. Assembles the exact prompt with pre-filled signal values (Prompt Layer)
3. Makes one LLM call to score the lead holistically (Rating Agent component)
4. Validates the output and enforces deterministic banding rules — which can override the LLM's bucket (Output Schema Layer)

The orchestrator sees only the `score_lead()` call and the `ScoringOutput | ScoringFailure` return. It never reaches inside.

**Execution type:** HYBRID — LLM judgment (step 3) + deterministic banding enforcement that can override LLM output (step 4). See [[analyses/execution-type-classification]] P1-5.

---

## Inputs

The orchestrator prepares and passes all inputs. The Rating Agent reads nothing from the data layer directly — the orchestrator owns all data fetching.

### Required Inputs

| Input | Type | Source | Prepared by |
|---|---|---|---|
| `tenant_id` | string | Run context | Orchestrator |
| `lead` | EnrichedLead | Post-normalisation lead record | Orchestrator (after P1-3 Normalise) |
| `variant` | enum: `new` \| `returning` \| `rescore` | Trigger context | Orchestrator |
| `signal_values` | dict `{signal_name: value}` | Lead Enrichment output | Orchestrator (after P1-2b signal extraction) |
| `prompt_template_version` | string | Active version from `prompt_registry` | Orchestrator (loaded at pre-flight) |

### Conditional Inputs (variant-dependent)

| Input | Type | Required when | Notes |
|---|---|---|---|
| `existing` | LeadRecord | `returning`, `rescore` | Prior lead record with previous scores and history |
| `touchpoints` | list[Touchpoint] | `returning` | Full interaction history with the tenant |

### What `lead` (EnrichedLead) contains

The EnrichedLead is the normalised lead record after all enrichment stages. It contains:
- Contact fields (name, phone, email — normalised)
- Company fields (industry, size, role — for B2B)
- Interaction history (messages, touchpoints, channel activity)
- Behavioural fields (page views, downloads, form completion)
- Context fields (source, campaign, geography tier)
- Data completeness score (0–100%, assigned by Normalise stage)

The signal_values dict is extracted *from* the EnrichedLead by the deterministic signal extraction step (P1-2b). Both are passed to the Rating Agent — the EnrichedLead provides full context; signal_values are the pre-computed answers to each signal question.

### The Three Prompt Variants

| Variant | When used | What changes |
|---|---|---|
| `new` | Lead has never been scored by this tenant | Baseline scoring prompt; no prior history in user message |
| `returning` | Lead has been scored before; has returned with new activity | Prior score + touchpoint history injected; prompt focuses on what changed |
| `rescore` | Lead is being re-evaluated after salesperson feedback | Prior score + feedback reason injected; prompt asks to re-evaluate with the feedback context |

Variant selection is the orchestrator's responsibility, not the Rating Agent's. The Rating Agent receives the variant as input.

---

## Internal Execution

### Component 1 — Persona Engine (AUTOMATION)

Loads the tenant's PersonaObject from cache or DB. Cache TTL: 15 minutes.

The PersonaObject carries: business_type, IcpDefinition, per-tenant scoring_weights, banding thresholds (hot_min, warm_min), custom rules, tone, and version. This is the context that makes scoring tenant-aware.

**Failure:** `PersonaNotFoundError` if no persona exists for this tenant. `PersonaInvalidError` if weights don't sum to 1.0. Both are hard failures — the lead is routed to human_review immediately (no LLM call attempted).

---

### Component 2 — Prompt Layer (AUTOMATION)

Assembles the exact prompt sent to the LLM.

**System message (static per tenant — cacheable by LLM provider):**
- Scoring rubric: how to evaluate each of the five dimensions
- Tenant persona and ICP definition injected
- Active dimension weights (from PersonaObject.scoring_weights)
- Output format instruction (JSON schema, field definitions)

**User message (per-lead variable):**
- Filled signal values from signal_values dict:

```
FIT SIGNALS:
  - industry_match    : true
  - role_relevance    : true
  - company_size_fit  : partial

INTENT SIGNALS:
  - pricing_request   : true
  - demo_requested    : false
  - urgency_language  : true
  - timeline_stated   : true

ENGAGEMENT SIGNALS:
  - response_speed    : fast
  - revisit_count     : 3
  - channel_diversity : multi

[... all signals across all dimensions ...]

DATA COMPLETENESS: 87%
```

**Prompt caching:** The system message is static per tenant per prompt version. LLM providers (OpenAI, Anthropic) cache prompt prefixes — meaning call 2 through N in a batch for the same tenant reuse the cached system message. This cuts token cost and latency for batch scoring runs.

**Failure modes:** `PromptAssemblyError` (missing required signal slot), `PromptTooLargeError` (exceeds model context window), `PromptVariantError` (unknown variant — orchestrator bug).

---

### Component 3 — Rating Agent component (LLM CALL)

Makes exactly one logical LLM call per lead. Owns everything related to the model provider: authentication, timeout, retries, rate limit handling, raw response parsing.

**Hard timeout:** 30 seconds for the LLM call itself (within the 60-second total Rating Agent timeout).

**Retry on transient errors:** Exponential backoff for rate limits, 5xx errors, network timeouts. Non-retryable errors (auth failure, bad request) fail immediately without retry.

**Provider-agnostic:** The Prompt Layer and Output Schema Layer do not know which provider served the request. The model is recorded in the output for lineage purposes.

**Open decision:** Primary provider — Groq (speed) vs OpenAI (reliability, caching support), or Groq primary with OpenAI fallback. `[TBD — team decision]`

---

### Component 4 — Output Schema Layer (AUTOMATION)

Transforms the non-deterministic LLM output into a guaranteed, typed ScoringOutput. The contract between LLM reasoning and the rest of the system.

**What it does:**

| Operation | Detail |
|---|---|
| Schema validation | Validates parsed JSON against canonical ScoringOutput schema |
| Coercion | Case normalisation on bucket string, score rounding, whitespace trimming |
| **Banding enforcement** | **If LLM bucket disagrees with `score + tenant banding thresholds`, banding wins. Discrepancy is logged.** |
| Lead completeness gate | If `lead_completeness` < configured threshold → `needs_review = true` |
| Schema version recording | Records schema_version on every output |
| Failure handling | Returns typed ScoringFailure — never a malformed success |

**Why banding enforcement is in this layer and not in Bucketize:**  
Bucketize (P1-7) is a separate downstream pipeline step that the orchestrator runs *after* the Rating Agent returns. The Output Schema Layer's banding check is different — it ensures the LLM's own bucket claim is internally consistent with the score it produced, within the same call. Bucketize then re-applies the full tenant threshold comparison to the final score (after any disqualification adjustments from P1-6).

---

## Outputs

### Score Output

| Field | Type | Description |
|---|---|---|
| `score` | int (0–100) | Overall lead score. Weighted combination of five dimension sub-scores. |
| `bucket` | string: `hot` \| `warm` \| `cold` | LLM's bucketing judgment, validated and enforced by Output Schema Layer banding rules. |
| `sub_scores` | object | Per-dimension score breakdown. Always present — never collapsed. Required for AP1, AP2 quality metrics and for salesperson-facing score explanations. |

**sub_scores current schema (from S2 intelligence layer design):**
```json
{
  "fit": 21,
  "intent": 22,
  "engagement": 17,
  "recency": 15
}
```

**Soft blocker:** S2's design doc defines 4 sub-score fields (fit, intent, engagement, recency) but the system has 5 scoring dimensions (Fit, Intent, Engagement, Behaviour, Context). Whether behavioural and context are separate fields or collapsed into engagement is not yet locked. `[S2 to clarify]`

**Why sub_scores must never be collapsed:** A lead that scores high on Intent but low on Fit requires completely different action than the reverse. The dimension breakdown is what makes the score actionable — without it, the salesperson receives a number with no explanation. All quality metrics that depend on scoring attribution (AP1, AP2, the feedback loop attribution step) require the full sub_scores object.

---

### Reasoning Output

| Field | Type | Description |
|---|---|---|
| `reasoning` | string | One-line natural language explanation of why this lead received this score. Written for the salesperson — not an internal log. Example: "Strong ICP fit and explicit high-intent signals (pricing, timeline, scope) from a multi-channel active lead." |
| `recommended_action` | string | Specific suggested next step. Example: "Call today — high intent, strong fit." Scoped to what a salesperson can act on immediately. |

**Scope of recommended_action:** The `recommended_action` field is intentionally simple at MVP — one sentence, actionable. This is deliberately limited. A future Recommendation Agent (see [[analyses/future-optional-agents]]) would replace this with a richer recommendation object including talking points, channel preference, and timing. The Rating Agent's responsibility is scoring; recommendation is a downstream concern.

---

### Completeness Output (previously called "confidence")

**Important naming correction (2026-04-22):** The intelligence layer design document uses the term "confidence" for this output field. The team has confirmed this is **not LLM self-assessed confidence.** LLMs are poorly calibrated at self-reporting certainty. This field is a **lead completeness score** — it measures how complete the enriched lead data was when the Rating Agent was called. A score of 0.87 means 87% of expected signal fields were present and populated. The routing logic and `needs_review` flag are unchanged; only the interpretation of the field changes.

See [[concepts/confidence-first-class]] for full correction history.

| Field | Type | Description |
|---|---|---|
| `lead_completeness` | float (0.0–1.0) | Fraction of expected signal fields that were populated in the enriched lead. Set by the Output Schema Layer based on data completeness score from Normalise stage. **This is not LLM confidence.** |
| `needs_review` | bool | Set to `true` by the Output Schema Layer when `lead_completeness` falls below the configured threshold. When `true`: the lead is still scored, still delivered — AND routed to human_review queue. Not a failure; a quality flag. |

**Lead completeness routing bands:**

| lead_completeness | What happens |
|---|---|
| ≥ 80% | Auto-assign bucket. Salesperson sees full score with no flags. |
| 50–79% | Assign bucket with WARNING flag. Salesperson can choose to review. |
| < 50% | `needs_review = true`. Lead routed to human_review queue. Score is still stored and visible. |

**Threshold for needs_review:** `[TBD — S2 suggests 0.6 or 0.75 as starting options; team decision]`

---

## Full ScoringOutput Schema

```json
{
  "score": 84,
  "bucket": "hot",
  "reasoning": "Strong ICP fit and explicit high-intent signals (pricing, timeline, scope) from a multi-channel active lead — recommend immediate outreach.",
  "lead_completeness": 0.87,
  "sub_scores": {
    "fit": 21,
    "intent": 22,
    "engagement": 17,
    "recency": 15
  },
  "recommended_action": "Call today — high intent, strong fit",
  "needs_review": false,
  "schema_version": "v1.0",
  "prompt_version": "v1.3.0",
  "model": "gpt-4o"
}
```

**ScoringFailure schema (returned when scoring cannot complete):**

```json
{
  "failure_reason": "timeout | malformed_output | rate_limit_exhausted | schema_mismatch",
  "retry_count": 2,
  "lead_id": "uuid",
  "prompt_version": "v1.3.0",
  "timestamp": "ISO-8601"
}
```

A ScoringFailure causes the orchestrator to route the lead to `pipeline_stage = 'human_review'` with `reason: scoring_failed`.

---

## Invocation Conditions

### When the Rating Agent is called

| Condition | Notes |
|---|---|
| Lead has reached `pipeline_stage = 'normalised'` | The orchestrator never calls the Rating Agent before normalisation is complete |
| Signal values have been extracted (P1-2b complete) | The Rating Agent requires pre-filled signal_values; it does not run detection_rules itself |
| Persona Agent output exists for this tenant | Pre-flight validation confirms this before any lead processing starts |
| Concurrency slot available for this tenant | Per-tenant concurrency cap (recommend 2 per tenant); waits in queue if cap is reached |

### Per-Tenant Concurrency Cap

The Rating Agent is the only LLM call per lead — and LLM calls are the most expensive and rate-limited resource in the system. The concurrency cap must be per-tenant, not global.

**Why per-tenant, not global:** A global cap of 5 allows one tenant's batch to fill all 5 slots, starving all other tenants. A per-tenant cap of 2 ensures that no single tenant can monopolize the LLM resource, regardless of batch size.

**Implementation:** A semaphore keyed on `tenant_id`. Before calling `score_lead()`, acquire the semaphore for that tenant. If 2 calls are already running for that tenant, the third waits in queue. On slot release, the next queued call enters.

**Recommended starting cap:** 2 per tenant. Tunable per-tenant via `tenant_config`. `[Team decision — depends on LLM provider rate limits]`

### Timeouts

| Level | Timeout | What happens on breach |
|---|---|---|
| LLM call (Rating Agent component) | 30 seconds | Retry once with extended deadline |
| Full `score_lead()` call | 60 seconds | ScoringFailure returned; lead routed to human_review |
| End-to-end pipeline budget | 90 seconds | Orchestrator-level timeout; escalation to admin |

---

## What the Rating Agent Does NOT Do

| Responsibility | Who owns it |
|---|---|
| Fetch lead data from channels | Data Gather (P1-1, AUTOMATION) |
| Collect additional lead enrichment data | Lead Enrichment Part A (P1-2a, AUTOMATION) |
| Extract signal values from enriched data | Lead Enrichment Part B (P1-2b, AUTOMATION) |
| Normalise and clean the lead record | Normalise (P1-3, AUTOMATION) |
| Apply disqualification rules | Disqualification Gate (P1-6, AUTOMATION) |
| Assign the final bucket to the lead | Bucketize (P1-7, AUTOMATION) — Rating Agent suggests bucket; Bucketize makes the final assignment after disqualification |
| Write the score to the data layer | Orchestrator (after Rating Agent returns) |
| Write lineage records | Orchestrator |
| Deliver lead cards to the chat interface | Delivery and Integration Layer |
| Generate personalized outreach messages | Future Recommendation Agent (see [[analyses/future-optional-agents]]) |
| Create or update the PersonaObject | Persona Agent |
| Load data from the data layer | Orchestrator (passes data as inputs) |

---

## Overlap Prevention — Where Rating Agent Ends

The Rating Agent's responsibility ends the moment `ScoringOutput | ScoringFailure` is returned to the orchestrator. From that point:

- The orchestrator writes the score to the data layer
- The orchestrator writes lineage (prompt_version, lead_completeness, sub_scores all recorded in lineage_record)
- The Disqualification Gate applies static overrides to the score
- Bucketize assigns the final bucket
- The Delivery Layer handles salesperson-facing output

The Rating Agent and Persona Agent never communicate directly. The Rating Agent receives Persona Agent outputs only as data — PersonaObject and signal definitions via the prompt template, both already stored in the data layer before any Pipeline 1 run begins.

---

## Failure Handling

| Failure mode | Retry? | Final outcome |
|---|---|---|
| Malformed JSON returned by LLM | Yes — 1 retry with schema reminder appended to prompt | If still failing: ScoringFailure → human_review |
| Output doesn't match expected schema | Yes — 1 retry | If still failing: ScoringFailure → human_review |
| LLM call timeout (30s) | Yes — 1 retry with extended deadline | If still failing: ScoringFailure → human_review |
| Rate limit hit | Yes — wait for rate limit window, then retry | If still failing: ScoringFailure → human_review |
| Two consecutive failures (any combination) | No more retries | ScoringFailure → `pipeline_stage = 'human_review'`, `reason: scoring_failed` |
| PersonaNotFoundError (no persona for tenant) | No | Lead halted; admin alerted; tenant onboarding must complete first |
| PersonaInvalidError (weights don't sum to 1.0) | No | Lead halted; persona must be repaired before scoring resumes |

**On any retry:** The `prompt_version` is recorded in the lineage log so that retry-driven scoring is attributable and auditable.

**Accepted trade-off (crash recovery):** If the orchestrator crashes mid-LLM-call and recovers, the Rating Agent will be called again for that lead. This means one extra LLM cost for the affected lead. This is accepted — the `prompt_version` in the lineage record makes any scoring drift visible and traceable. See [[analyses/orchestration-layer-spec]] Section 8.4.

---

## Observability

Every Rating Agent call emits the following signals (written by orchestrator to lineage_record after the call):

| Signal | What it captures |
|---|---|
| `prompt_version` | Which prompt template was used — core attribution signal for the feedback loop |
| `model` | Which LLM model served this call |
| `tokens_in` | Input token count — LLM cost metering |
| `tokens_out` | Output token count — LLM cost metering |
| `latency_ms` | End-to-end duration of `score_lead()` call |
| `retry_count` | How many times this call was retried |
| `needs_review` | Whether completeness gate triggered review routing |
| `schema_validation_result` | `pass` / `coerced` / `failed` — Output Schema Layer result |
| `lead_completeness` | The completeness score that drove needs_review |
| `sub_scores` | Per-dimension breakdown — feeds AP1, AP2 quality metrics |

LLM cost metering at the per-call level is required for tenant-level cost attribution. See [[analyses/service-scaling-strategy]] Recommendation 15.

---

## Open Decisions

| Decision | Status |
|---|---|
| Primary LLM provider (Groq vs OpenAI, or fallback chain) | `[TBD — team decision]` |
| Model config scope: global vs per-tenant override | `[TBD — team decision]` |
| Prompt storage: in code (git-versioned) vs data layer (editable without deployment) | `[TBD — team decision]` |
| sub_scores field list: 4 fields (current S2 spec) vs 5 fields (matching 5 dimensions) | `[Soft open — S2 to clarify]` |
| needs_review threshold: 0.6 (lenient) or 0.75 (conservative) | `[TBD — team decision after Month 1]` |
| Per-tenant concurrency cap starting value | Recommend 2 per tenant; `[team decision based on provider rate limits]` |
| Bucket disagreement logging: log only vs surface as dashboard alert | `[TBD — team decision]` |

---

## Related Documents

- [[analyses/persona-agent-spec]] — builds the PersonaObject and signal definitions that the Rating Agent consumes
- [[analyses/future-optional-agents]] — Recommendation Agent and Workflow Agent as future extensions
- [[analyses/execution-type-classification]] — P1-5 Scoring step (HYBRID) detailed breakdown
- [[analyses/orchestration-layer-spec]] — Section 4.3 Stage 4 (Scoring Agent detail), Section 8 (state tracking)
- [[concepts/intelligence-layer]] — four internal components of the `score_lead()` call
- [[concepts/signal-types]] — five scoring dimensions; sub_scores structure
- [[concepts/confidence-first-class]] — naming correction: lead_completeness vs confidence
- [[analyses/scoring-quality-metrics]] — quality metrics that depend on Rating Agent outputs (sub_scores, prompt_version, lead_completeness)
