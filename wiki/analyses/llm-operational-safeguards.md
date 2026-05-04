---
type: analysis
question: "What are the production-ready retry, fallback, prompt caching, token monitoring, and cost control safeguards for the LLM system?"
date: 2026-05-05
tags: [llm, reliability, retry, fallback, caching, token-monitoring, cost-control, rating-agent, pipeline-1, operational]
sources_consulted:
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/service-scaling-strategy]]"
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/orchestration-layer-spec]]"
status: COMPLETE
---

# LLM Operational Safeguards

**Question:** What are the production-ready retry, fallback, prompt caching, token monitoring, and cost control safeguards for the LLM system?
**Date:** 2026-05-05

---

## Answer / Finding

This document defines three operational safeguards for the LLM layer of the Lead Intelligence Engine. These safeguards ensure the system does not crash under failure, does not waste money, and does not produce inconsistent outputs.

All rules here are **exact** — no vague terms like "retry a few times." Every number is stated explicitly so the system behaves predictably in production.

The three safeguards are:

1. **RETRY_STRATEGY** — what to do when an LLM call fails
2. **FALLBACK_STRATEGY** — what to do when all retries are exhausted
3. **CACHING_AND_TOKEN_CONTROL** — how to manage cost and avoid redundant work

---

## RETRY_STRATEGY

### The Basic Rule

Every LLM call gets a maximum of **2 total attempts** — the original call, plus one retry if the first fails. There is never a third attempt. After 2 failed attempts, the system moves on to the Fallback Strategy.

The retry counter is per-call, per-lead. It resets for every new lead. It does not carry over.

Every attempt — whether it succeeds or fails — writes the following to `lineage_record`: `lead_id`, `tenant_id`, `attempt_number`, `failure_type`, `timestamp`. This is non-negotiable for auditability.

---

### Case 1 — Timeout Errors

A timeout means the LLM took too long to respond.

**Rules:**

- Attempt 1 timeout limit: **30 seconds**
- Attempt 2 timeout limit: **45 seconds** (given more time because network conditions sometimes cause brief slowdowns)
- Delay before retrying: **none** — fire the retry immediately after the timeout is detected
- What counts as a timeout: any call that does not return a response within the time limit
- Stop condition: if attempt 2 also times out, stop — no more retries, move to Fallback Strategy
- Log: `failure_type = "timeout"`, `latency_ms`, `attempt_number`

---

### Case 2 — Invalid JSON / Schema Mismatch

This means the LLM returned something, but it did not match the expected output format.

**Rules:**

- Delay before retrying: **none** — the problem is in the output format, not a network issue, so waiting does not help
- Attempt 2 gets a correction message added to the end of the user message. The correction message states the exact rule that was violated, followed by: *"Return a single valid JSON object exactly matching the schema. No other text."*
- Stop condition: if attempt 2 still fails schema validation, stop — move to Fallback Strategy

**Retry for any of these conditions:**
- Response is not valid JSON (syntax error)
- Any required output field is missing
- A field has the wrong data type (e.g., a string where an integer was expected)
- An enum field contains a value that is not in the allowed list
- A number is outside its allowed range
- A cross-field rule is violated beyond its allowed tolerance (SUB_SCORES_SUM ±1, COMPLETENESS_ECHO ±0.001)

**Do NOT retry for these — halt immediately and alert admin:**
- `PersonaInvalidError` — the tenant's scoring weights don't add up to 1.0. This is a configuration problem. Retrying will produce the same error.
- `PersonaNotFoundError` — no persona exists for this tenant. Scoring cannot proceed until onboarding is complete.
- `InputValidationError` — the data going *into* the call is invalid. Retrying with the same bad input will always fail.

These three errors are never caused by LLM behavior. Retrying them wastes a call and produces no benefit.

- Log: `failure_type = "malformed_json"` or `"schema_mismatch"`, the specific rule that failed, `attempt_number`

---

### Case 3 — Transient API Failures (Rate Limits, Server Errors, Network Issues)

These are failures caused by the provider or network, not by the LLM's output quality.

**Rate limit (HTTP 429):**

A rate limit means the provider is saying "slow down, you are sending too many requests."

- Read the `Retry-After` header from the API response — this tells you exactly how many seconds to wait
- **If `Retry-After` is 25 seconds or less:** wait that many seconds, then retry
- **If `Retry-After` is greater than 25 seconds, or if the header is absent:** do NOT retry this request at all — return ScoringFailure immediately with `failure_reason = "rate_limit_exhausted"` and let the orchestrator re-queue this lead for later

**Why not just wait longer and retry?** The 60-second total budget for a `score_lead()` call does not have room for a long wait. Retrying after only 5 seconds when the provider said to wait 60 would produce another 429 instantly, wasting the only retry attempt on a call that was never going to succeed. It is better to return a clean ScoringFailure and try the lead again in the next batch.

**Server error (HTTP 5xx):**
- These are temporary problems on the provider's side
- Wait **2 seconds** before retrying (a brief pause lets the provider recover from whatever caused the error)
- If attempt 2 also returns 5xx, stop — move to Fallback Strategy

**Network timeout or connection error:**
- Retry immediately, no wait

**Auth failure (HTTP 401 or 403):**
- Do NOT retry
- Do NOT silently fail this lead and move on
- **Fire an admin alert immediately** — a 401/403 means the API key is invalid, expired, or revoked; this is a production incident that will block every scoring call until it is fixed, not just one lead
- Route the lead to human_review, but the alert must fire before anything else

**Bad request (HTTP 4xx other than 429 and 401/403):**
- Do NOT retry — a bad request will always produce the same error with the same input
- Route to human_review, log the status code

- Log for all transient failures: `failure_type` (one of: "rate_limit", "provider_5xx", "network_error", "auth_failure"), HTTP status code where applicable, `attempt_number`

---

## FALLBACK_STRATEGY

### The Two-Layer Model

This system has two separate fallback layers. They operate in sequence and serve different purposes.

---

### Layer 1 — Provider Fallback (Handled by LiteLLM, Transparent to the Rating Agent)

**What it is:**

LiteLLM is the library that sits between the Rating Agent and the actual LLM providers (Anthropic, OpenAI). It acts as a switchboard. The Rating Agent calls LiteLLM; LiteLLM decides which provider to use.

**How it works:**

The primary provider is **Anthropic Claude Sonnet 4.6**. LiteLLM is configured with **OpenAI GPT-4o** as a fallback provider.

If LiteLLM sends a call to Claude and receives an error that means Claude is unavailable (not a schema error — a connectivity or provider outage), it automatically re-routes the same call to GPT-4o. This re-routing happens *within* what the Rating Agent considers Attempt 1. The Rating Agent's retry counter does **not** increment for a provider-level re-route.

**Important:** LiteLLM does not proactively test providers for health before calling them. It detects unavailability from error responses in real time and re-routes based on those. There is no pre-flight health check.

**What stays the same when GPT-4o is serving the call:**
- The same prompt is sent
- The same JSON output schema is enforced
- The same token metering (tokens_in, tokens_out) still applies and is logged
- The same retry rules from above still apply if GPT-4o also returns a bad response

**What changes:**
- The `model` field in `lineage_record` will show `"gpt-4o"` instead of `"claude-sonnet-4-6"` — this is how you know a fallback occurred
- Cost per token is different for GPT-4o; the cost is still calculated and logged correctly because pricing is read from config (see Caching and Token Control section)
- Anthropic prefix caching does not apply to GPT-4o calls — cached_tokens_in will be 0

**Hard failure:** If GPT-4o also fails, LiteLLM raises an exception. The Rating Agent receives this as a transient provider error and handles it through normal retry logic.

---

### Layer 2 — ScoringFailure (Fires After All Retries on All Providers Are Exhausted)

**Trigger condition:**

Two consecutive failed attempts from any combination of: `malformed_json`, `schema_mismatch`, `timeout`, `transient_provider_error_5xx`, `rate_limit_exhausted` — after LiteLLM has already attempted provider fallback.

**What happens:**

The Rating Agent returns a typed `ScoringFailure` object. It is not an exception or a crash — it is a clean, structured response that tells the orchestrator exactly what went wrong.

ScoringFailure contains:
- `failure_reason` — one of: `timeout` / `malformed_output` / `rate_limit_exhausted` / `schema_mismatch` / `provider_error`
- `retry_count` — integer (0, 1, or 2)
- `lead_id` — UUID of the affected lead
- `prompt_version` — which prompt template was in use when the failure happened
- `timestamp` — when the failure occurred

**Orchestrator action upon receiving ScoringFailure:**
- Set `pipeline_stage = 'human_review'` with `reason = 'scoring_failed'` on the `leads` table
- Write a `lineage_record` with the full failure context
- The lead is NOT lost — it sits in the human_review queue for manual scoring

**Terminal state:** ScoringFailure is the end of the road for this call invocation. The lead will not be automatically retried again within the same pipeline run. A human can re-trigger scoring manually from the human_review queue once the underlying issue is resolved.

**What does NOT reach Layer 2:**

`PersonaInvalidError` and `PersonaNotFoundError` bypass both layers entirely. These halt the specific lead immediately, alert the admin, and do not produce a ScoringFailure. They represent broken configuration, not a transient call failure.

---

## CACHING_AND_TOKEN_CONTROL

### Caching Strategy

**Two separate caches exist. They serve different purposes.**

---

**Cache 1 — Anthropic API Prompt Prefix Cache**

*What gets cached:* The static part of the prompt — the scoring rubric, the tenant's ICP definition, the signal definitions, and the output format instructions. This is called the "system message."

*How it works:* Anthropic automatically caches the system message after the first call. For calls 2 through N in the same batch for the same tenant, Anthropic reuses the cached version instead of re-processing it. This cuts both cost (cached tokens cost 90% less than normal tokens) and latency.

*What you must do to get cache hits:* Keep the system message byte-for-byte identical across all leads for the same tenant. All per-lead data (signal values, lead profile, touchpoints) must go into the user message only — never into the system message.

*TTL:* 5 minutes — set by Anthropic, not configurable by us.

*Bypass:* Not possible to bypass. It is automatic.

---

**Cache 2 — PersonaObject Cache (In-Memory / Redis)**

*What gets cached:* The tenant's complete scoring configuration — ICP definition, dimension weights, banding thresholds (hot_min, warm_min), signal definitions. This is the data the Persona Agent built in Pipeline 2.

*Why it's cached:* Loading the PersonaObject from the database on every single lead call would add database round-trips to every scoring call. For a batch of 50 leads, that is 50 unnecessary DB reads. The PersonaObject rarely changes — caching it is safe.

*Cache key format:* `tenant:{uuid}:persona:{version}` — for example: `tenant:a3f1-...:persona:v2.1.0`. The version is always included so that updating the PersonaObject produces a different cache key automatically. A stale version can never be accidentally served after an update.

*TTL:* 15 minutes.

*When to invalidate immediately (do not wait for TTL):*
- A `PersonaInvalidError` has been repaired by the admin. The fixed persona must be loaded fresh — serving a repaired persona from a stale cache entry would re-introduce the error.
- The `persona_version` in the database is newer than the version in the cached key. This check happens at cache-read time before every batch run.

---

### Token Monitoring

**Per-request token budget by tenant tier:**

| Tier | Max tokens per request (input + output combined) |
|---|---|
| Basic (MVP default) | 4,000 |
| Standard | 8,000 |
| Premium | No hard cap; alert fires at 12,000 |

**How token usage is tracked:**

Every LLM API response includes three usage numbers: `input_tokens`, `output_tokens`, and `cached_tokens_in`. All three are recorded on every call in `lineage_record`.

LiteLLM's per-tenant virtual keys track cumulative usage independently as a secondary check. Each tenant gets their own virtual key, so LiteLLM's usage logs are already split by tenant.

**What happens when the token budget would be exceeded:**

*Before the call* — estimate the token count from the assembled prompt. If the estimate exceeds the tenant's per-request budget, truncate the `touchpoints` array (lowest-priority field, longest in character count) until the estimate fits within budget. Never truncate required signal fields or the persona context — those are the fields the LLM needs to score the lead correctly.

Use a tokenizer library (e.g., Anthropic's token counting endpoint or `tiktoken` for estimation) to produce the estimate. Do not guess.

*Hard block before the call* — if prompt assembly would produce more than **16,000 tokens** (Sonnet 4.6's practical limit for reliable structured output), return a `PromptTooLargeError` immediately. Do not call the LLM. Route the lead to human_review with `reason = 'prompt_too_large'`.

*After the call* — if actual tokens used exceeded the budget (because the output was longer than the estimate), log an overage event to `usage_record`. Do not reject the output — it is still valid. Include the overage in billing reconciliation.

---

### Cost Control

**How cost per request is calculated:**

Cost is calculated at call time. The formula is:

```
cost = (tokens_in × price_per_input_token)
     + (cached_tokens_in × price_per_cached_input_token)
     + (tokens_out × price_per_output_token)
```

**Critical rule — pricing must be read from a config table, not hardcoded.** Provider pricing changes over time. If the dollar values are hardcoded in the application, a price change will silently produce wrong cost records. Store provider pricing in a `provider_pricing_config` table. The application reads from that table at call time.

Stored in `usage_record` per call: `tenant_id`, `lead_id`, `model`, `tokens_in`, `tokens_out`, `cached_tokens_in`, `cost_usd`, `timestamp`.

Store **both** the raw token counts and the calculated `cost_usd`. Raw counts let you recalculate cost if pricing is corrected retroactively. Calculated cost is what reporting surfaces display. Storing only one or the other creates an audit gap.

---

**Daily and monthly cost caps:**

| Scope | Alert fires at | Hard stop fires at |
|---|---|---|
| Per-tenant per day | 80% of configured cap | 100% of configured cap |
| System-wide per month | 80% of configured cap | 100% of configured cap |

Default values at MVP:
- Per-tenant daily cap: **$5.00** (configurable per tenant in `tenant_config`)
- System monthly cap: **$100.00** (configurable in `system_config`)

**What happens at each threshold:**

At 80% of per-tenant daily cap:
- Send an alert to the tenant's team lead (via the notification channel configured in their tenant record)
- Scoring continues normally

At 100% of per-tenant daily cap:
- New scoring calls for that tenant are placed in a queue but not executed
- Calls already in-flight are allowed to complete
- The queue resumes automatically at **midnight UTC** when the daily cap resets
- Other tenants are completely unaffected

At 80% of system monthly cap:
- Send an alert to the system admin
- No action required yet — scoring continues for all tenants

At 100% of system monthly cap:
- Hard stop on all new scoring calls across all tenants
- The admin must manually lift the cap or wait for the calendar month to roll over
- This is an admin-only action — it requires explicit human approval

**Anomaly detection:**

If a single lead's LLM call costs more than **3× the rolling 7-day average per-lead cost** for that tenant, write an anomaly event to `usage_record`. Do not fail the call — the output may be perfectly valid. Flag it for admin review. This catches situations like an unusually large lead record being sent to the LLM, or an output that ran unexpectedly long.

---

## Evidence

- Retry max attempts (2), timeouts (30s/45s/60s), retry triggers, no-retry triggers: [[analyses/llm-io-contract]] VALIDATION_RULES retry_policy
- ScoringFailure schema and orchestrator routing to human_review: [[analyses/llm-io-contract]] VALIDATION_RULES fallback_behavior; [[analyses/rating-agent-spec]] Failure Handling
- LiteLLM as provider abstraction with Claude primary and GPT-4o fallback: [[analyses/tech-stack-research]] Locked Decisions table
- Prompt caching via system message (static) vs user message (per-lead): [[analyses/rating-agent-spec]] Component 2 — Prompt Layer; [[analyses/service-scaling-strategy]] Recommendation 8
- PersonaObject cache TTL 15 minutes: [[analyses/rating-agent-spec]] Component 1 — Persona Engine
- Token budget tiers (4K / 8K / unlimited): [[analyses/service-scaling-strategy]] Tiering table
- Per-tenant token and cost metering written to lineage_record: [[analyses/rating-agent-spec]] Observability; [[analyses/service-scaling-strategy]] Recommendation 15
- Per-tenant concurrency cap (semaphore by tenant_id): [[analyses/service-scaling-strategy]] Recommendation 6; [[analyses/rating-agent-spec]] Per-Tenant Concurrency Cap
- pipeline_stage = 'human_review' with reason = 'scoring_failed': [[analyses/service-scaling-strategy]] critical fix; [[analyses/orchestration-layer-spec]]

---

## Corrections Applied (Self-Audit)

This document corrects four flaws identified in the prior draft:

| Flaw | Prior version | Corrected version |
|---|---|---|
| Rate limit retry logic | If Retry-After > 25s, wait 5s and retry anyway | If Retry-After > 25s, skip retry entirely — return ScoringFailure with rate_limit_exhausted and let orchestrator re-queue |
| LiteLLM fallback description | "LiteLLM detects unavailability via internal health check" | LiteLLM detects unavailability from error responses in real time; no proactive health check; re-route happens within Attempt 1 without incrementing retry counter |
| Provider pricing hardcoded | Specific dollar values stated in the document | Pricing must be read from a config table; document states the formula, not hardcoded values |
| Auth failure (401/403) handling | Silently fail the lead, no escalation | Immediately fire admin alert — a 401/403 is a production incident that blocks all scoring until resolved, not a per-lead failure |

---

## Caveats & Gaps

- **Re-queue mechanism for rate_limit_exhausted not fully designed.** When a lead's scoring call returns ScoringFailure with reason = rate_limit_exhausted, it goes to human_review. An alternative would be an automatic delayed re-queue in the orchestrator (wait for rate limit window, then retry). This is not yet designed — it would require a scheduled retry mechanism in the workflow engine. For MVP, human_review is the safe default.
- **Token estimation library not chosen.** The document says to use a tokenizer library to estimate prompt token count before the call. The specific library is not locked — `tiktoken` (OpenAI's library) estimates Anthropic token counts with reasonable accuracy but is not exact. The Anthropic SDK's `count_tokens()` method is exact but adds a network round-trip. Team decision needed.
- **`provider_pricing_config` table not yet in the data entity model.** A dedicated pricing config entity is implied but not yet in the 32-entity data model. This table needs to be added before cost tracking can be implemented.
- **Anomaly detection threshold (3× rolling 7-day average) is a starting estimate.** This number should be calibrated after Month 1 when real per-lead cost data is available.

---

## Follow-up Questions

- Should rate_limit_exhausted leads be automatically re-queued after the rate limit window clears, rather than going to human_review? If yes, the workflow engine (Temporal or Step Functions — pending team decision) should own this retry scheduling.
- Which tokenizer library is used for pre-call token estimation: `tiktoken` (fast, approximate) or Anthropic SDK `count_tokens()` (exact, adds latency)?
- Where does `provider_pricing_config` live — as a database table, a config file in the repo, or an environment variable? Database is the most flexible for runtime changes; env var is the simplest for MVP.
- Should the anomaly detection threshold (3×) be global or per-tenant? A B2C tenant with short leads and a B2B tenant with rich company profiles will have very different per-lead average costs.
