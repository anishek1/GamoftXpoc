---
type: analysis
question: "What is the test strategy for the Lead Intelligence Engine — what is tested, at what layer, and what gates a PR or merge to main?"
date: 2026-05-20
tags: [testing, test-strategy, unit-tests, integration, e2e, llm-evaluation, ci-cd, quality]
sources_consulted:
  - "[[analyses/execution-type-classification]]"
  - "[[analyses/scoring-quality-metrics]]"
  - "[[analyses/core-use-cases]]"
  - "[[analyses/llm-io-contract]]"
  - "[[analyses/orchestration-layer-spec]]"
status: COMPLETE
---

# Test Strategy — Lead Intelligence Engine

**Question:** What is the test strategy for the Lead Intelligence Engine — what is tested, at what layer, and what gates a PR or merge to main?
**Date:** 2026-05-20

---

## Plain-English Summary

**Why this exists:** The system has three execution types — AUTOMATION, AGENT, and HYBRID (defined in [[analyses/execution-type-classification]]). Each requires a fundamentally different testing approach. Applying unit tests to LLM outputs is meaningless; applying only evaluation suites to deterministic signal extractors misses bugs that a unit test catches in seconds. This document maps every testable component to the correct layer so no engineering effort is wasted and no critical path is left untested.

**The governing rule from [[analyses/execution-type-classification]]:**
- **AUTOMATION** steps → unit tests (deterministic: same input always produces same output)
- **AGENT** steps → evaluation suites (statistical: distribution of outputs across representative leads)
- **HYBRID** steps → both: unit tests for the deterministic component, evaluation for the LLM component

---

## Testing Philosophy

**What we test:**
1. **Scoring math correctness** — every deterministic scoring rule must produce the exact same output for the same input, every time
2. **Enrichment isolation** — external API calls are mocked; tests validate the system's handling logic, not provider availability
3. **Pipeline stage reliability** — every `pipeline_stage` transition is verified; no lead can be silently lost between stages
4. **LLM output quality** — since LLM outputs are non-deterministic, we define acceptance thresholds per quality dimension and fail the build on regression

**What we do NOT test here:**
- LLM output determinism (non-deterministic by nature — evaluation suites handle this)
- Enrichment provider uptime (ops concern, not a code test)
- Whether tenant signal definitions are "correct" for their business (AI/ML evaluation concern, not code)

---

## Test Pyramid

### Layer 1 — Unit Tests

Fast, no I/O, fully deterministic. Target: full suite completes in under 60 seconds.

**Scope: all AUTOMATION steps and the deterministic component of all HYBRID steps.**

| Component | What is tested | Why it matters |
|---|---|---|
| Signal extractors (all 13 types) | Given a lead data object → extractor returns correct `(detected: bool, value: float, evidence: str)` | Foundation of scoring accuracy; deterministic by design; bugs here silently corrupt every score |
| Output Schema Layer — banding enforcement | LLM returns `bucket: "hot"`, score = 72, threshold = 80 → bucket overridden to `"warm"` | HYBRID Component B; tenant-configured thresholds are authoritative |
| Output Schema Layer — completeness gate | `lead_completeness < threshold` → `needs_review` set to `true` | Business rule; must be exact |
| Output Schema Layer — schema coercion | `bucket: "HOT"` → lowercased to `"hot"`; score rounded to integer | Minor inconsistencies corrected by rule |
| Data normalization (Normalise stage) | E.164 phone format, ISO 8601 dates, city-tier mapping (1/2/3), Title Case names | Malformed data propagates to enrichment and scoring |
| Bucket assignment (Bucketize) | score ≥ 80 → HOT; ≥ 55 → WARM; < 55 → COLD | Threshold comparison must never regress |
| Deduplication | Phone match wins; email second; name+location fallback | Duplicate leads double-count pipeline costs |
| Pre-flight validation | Missing persona → HALT; missing signals → HALT; missing prompt template → HALT | Prevents silent partial runs |
| Disqualification gate | Geography penalty (−30), role penalty (−40), spam force-zero | Score overrides are business rules; must be exact |
| Lead completeness routing | `needs_review = true` → `pipeline_stage = 'human_review'` set | Routing must never silently fail or skip |
| Prompt template fill | Named slot `{pricing_request}` → correct signal value substituted | Wrong slot = corrupted LLM input |
| Intent gate routing | `intent_specificity = very_low` AND `fit = HIGH` → `awaiting_clarification` | Pause condition must be exact |
| Lineage write sequence | Order: `lineage_record` → `task_execution` → `pipeline_run` → `pipeline_stage` (last) | Crash safety guarantee; wrong order = unrecoverable on crash |
| Feature flag enforcement | `enrichment.apollo = false` → Apollo not called; signals recorded as `not_detected` | Tenant config must be respected per run |
| Signal contribution math (C5) | Same signal + same weight + same value → always same score contribution | See [[analyses/scoring-quality-metrics]] C5 |

**Coverage expectation:**
- Signal extractors and Output Schema Layer banding: **100%** — these are the highest-value tests
- All other AUTOMATION components: **90%+**

---

### Layer 2 — Integration Tests

Mocked external I/O. Tests behavior at service and pipeline-stage boundaries.

| Scenario | Mocked | Verified |
|---|---|---|
| Enrichment provider calls | Each provider API returns a fixture response | Correct fields populated; fallback chain fires on empty response |
| Pipeline stage transitions | DB transitions: `captured` → `enriched` → `normalised` → `scored` → `delivered` | No stage is skipped; `pipeline_stage` is always last write |
| Rating Agent (Sonnet) call | Returns a mocked `ScoringOutput` JSON | Output Schema Layer processes correctly; banding + completeness gate fire |
| Message Parser (Haiku) call | Returns mocked extracted fields | Downstream signal extraction receives correct structured input |
| Meta webhook payload | Raw webhook bytes + `X-Hub-Signature-256` header | HMAC validation passes on correct signature; 403 on tampered payload |
| JWT validation + RLS | Valid and invalid Clerk JWTs | Correct `tenant_id` set in Postgres session; 401 on missing/expired token; 403 on wrong role |
| Crash recovery | Lead in non-terminal stage with `last_updated` > timeout | Orchestrator resumes from correct `pipeline_stage`; no stage is re-run unnecessarily |
| Concurrency guard — `awaiting_clarification` | Lead in `awaiting_clarification` state | Not picked up by crash recovery; 24h timeout handled separately |
| Feature flag check | `enrichment.truecaller = false` | Truecaller not called; signals from Truecaller recorded as `not_detected` |
| Pre-flight check on `onboarding` tenant | `tenant.status = 'onboarding'` | Pipeline 1 enqueues but does not execute |
| Queue drain on activation | `tenant.status` transitions `onboarding` → `active` | All `captured` leads from event gap window are processed in order |
| `needs_review` routing | `lead_completeness = 0.35`, threshold = 0.60 | `pipeline_stage = 'human_review'`; lead appears in human review queue |
| Audit log write failure | DB unavailable for `access_log` insert | Primary API request completes; failure emitted as high-priority metric |
| Pydantic validation on inbound lead | Unknown field in `LeadIngestRequest` | HTTP 422; request rejected before application logic |

---

### Layer 3 — E2E Tests

Full pipeline execution against a dedicated test tenant. **No mocks.** The complete pipeline runs against real infrastructure (staging environment or local Docker compose — to be decided by team).

Three mandatory golden paths, derived from [[analyses/core-use-cases]]:

---

**Golden Path 1 — HOT B2B Lead (Use Case 1)**

Input: WhatsApp DM with explicit buying intent. Company verifiable via Apollo.

Expected pipeline outcome:
- `pipeline_stage` sequence: `captured → fetched → enriched → normalised → scored → delivered`
- Score ≥ 80, bucket = `hot`
- `recommended_action` = `call_immediately`
- `lead_completeness` ≥ 0.80
- `needs_review = false`
- Push notification dispatched to salesperson
- HOT SLA timer started (24-hour window)
- `lineage_record` written at every stage with correct `prompt_version` and `model`
- Lead card appears in delivery layer within 120 seconds of message arrival (OP1)

Failure condition: any of the above absent = golden path 1 broken; block merge.

---

**Golden Path 2 — COLD SMB Fragmented Lead (Use Case 2)**

Input: WhatsApp DM from unverifiable SMB owner with bulk order intent. Company not in any registry.

Expected pipeline outcome:
- `pipeline_stage` sequence: `captured → fetched → enriched → normalised → scored → human_review`
- Score 35–50, bucket = `cold`
- `lead_completeness` ≤ 0.45
- `needs_review = true`
- `pipeline_stage = 'human_review'`
- Lead card includes qualification note: "Ask for GST number or formal business name to verify"
- Lead appears in human review queue, visible to team lead

Failure condition: lead silently dropped or `pipeline_stage = 'failed'` without correct routing = golden path 2 broken; block merge.

---

**Golden Path 3 — NOISE / Early Exit (Use Case 3)**

Input: Single emoji or one-word greeting DM ("👍", "hi").

Expected pipeline outcome:
- Message Parser returns `proceed: false`, `discard_reason` populated
- `pipeline_stage = 'insufficient_signal'` — set immediately after pre-filter gate
- No enrichment API called (zero provider calls)
- No Scoring Agent called (zero LLM cost)
- No lead card created for salesperson
- Discard event written to `intake_event_log` with `discard_reason`
- Discard rate incremented in quality snapshot

Failure condition: lead reaches enrichment stage or appears in salesperson UI = golden path 3 broken; block merge.

---

## LLM Evaluation Suite

Separate from the test pyramid. Runs against the real LLM provider. Does not replace unit tests — it validates what unit tests cannot.

**Triggered on any PR that changes:**
- A prompt template
- A signal definition
- The LLM model version
- The LLM I/O contract version (INPUT_SCHEMA or OUTPUT_SCHEMA)

**Evaluation dimensions (per [[analyses/llm-io-contract]] OUTPUT_SCHEMA):**

| Dimension | What is checked | Gate threshold |
|---|---|---|
| Schema compliance | LLM output passes `OUTPUT_SCHEMA` validation | 100% — any failure = regression |
| Sub-score sum | `sub_scores.fit + intent + engagement + behaviour + context == score` (±1 tolerance) | 100% |
| Bucket consistency | LLM-returned bucket matches score + tenant banding thresholds | 100% (Output Schema Layer enforces; flag if banding overrides > 5%) |
| `recommended_action` enum | Value is one of the 7 defined enum values | 100% |
| Reasoning presence | All 4 `reasoning` sub-fields present and non-empty | 100% |
| HOT bucket regression | Percentage of golden HOT leads still scored HOT after change | TBD after Month 1 baseline |

**Golden test set:** Minimum 10 synthetic leads per bucket (HOT B2B, WARM B2B, COLD B2B, COLD SMB fragmented, NOISE). Separate test sets for B2B and B2C tenant configs. No real PII — all synthetic.

**Regression detection:** If schema compliance drops below 100% or bucket regression exceeds threshold, PR is blocked.

---

## CI/CD Gates

| Event | Tests that must pass | Blocks merge |
|---|---|---|
| PR opened / updated | All unit tests | Yes |
| PR opened / updated | All integration tests | Yes |
| PR changes prompt / signal / model / schema | LLM evaluation suite (regression check) | Yes |
| Merge to main | Full unit + integration suite | Yes |
| Merge to main | E2E golden paths (all 3) | Yes |
| Merge to main | LLM evaluation suite | Yes |

---

## Coverage Expectations per Service

| Service | Unit | Integration | Note |
|---|---|---|---|
| Signal Extractor Registry | **100%** | — | Highest-priority; bugs silently corrupt all scores |
| Output Schema Layer | **100%** | — | Business rule enforcement; must be exact |
| Orchestration Service (stage logic) | 80%+ | 80%+ | Pipeline transitions + lineage write order |
| Enrichment Service | 70%+ | 80%+ (mocked APIs) | Fallback chain logic + consent gate |
| Message Parser (Haiku) | — (LLM) | Integration w/ mocked output | Evaluated in LLM eval suite |
| Rating Agent (Sonnet) — banding only | **100%** (banding) | Integration w/ mocked output | Unit test the AUTOMATION component; eval suite for LLM component |
| Delivery Service | 60%+ | 70%+ | Channel dispatch + notification routing |
| Governance / Lineage | 80%+ | 80%+ | Write order correctness is critical |
| Auth Middleware | 80%+ | **90%+** | JWT validation + RLS activation is security-critical |
| Webhook Receiver | — | **90%+** (HMAC + schema) | HMAC validation is security-critical |

---

## Test Data & Fixtures

**Test tenant:** `tenant_id = "test-tenant-001"` with:
- Locked `PersonaObject` (B2B, tech industry, mid-market)
- Scoring weights: Fit 25 / Intent 25 / Engagement 20 / Behaviour 20 / Context 10
- 10 pre-defined signals across 5 dimensions
- `prompt_template_version = "v1.0.0-test"` (locked, never changed by evaluation runs)
- Bucket thresholds: HOT ≥ 80, WARM ≥ 55, COLD < 55

**Lead fixtures (synthetic, no real PII):**

| Fixture | Bucket | `lead_completeness` | Path |
|---|---|---|---|
| `fixture_hot_b2b.json` | HOT | 0.88 | DM path, all intent signals true |
| `fixture_warm_b2b.json` | WARM | 0.67 | DM path, partial intent signals |
| `fixture_cold_smb.json` | COLD | 0.38 | DM path, company unverifiable |
| `fixture_noise.json` | — (discarded) | — | Pre-filter gate exit |
| `fixture_lead_ad_hot.json` | HOT | 0.90 | Lead Ad path (skips Message Parser) |
| `fixture_b2c_hot.json` | HOT | 0.82 | B2C path (add once Urvee Organics persona locked) |

**Enrichment API mock library:** One mock response per provider per fixture lead. Stored alongside fixtures, versioned with them.
- Apollo mock for HOT: returns full company profile
- Apollo mock for COLD SMB: returns empty result → triggers fallback chain
- Truecaller mock for HOT: returns name match
- All other providers: minimal valid responses for standard fixtures

---

## Caveats & Gaps

- **`needs_review` threshold** is TBD (0.60 or 0.75). Unit tests for the completeness gate use a configurable placeholder. Update fixture and test assertion when team decides — see [[analyses/llm-io-contract]] open decisions.
- **B2C E2E golden path** cannot be written until Urvee Organics persona is configured. `fixture_b2c_hot.json` is a placeholder.
- **LLM evaluation thresholds** for HOT bucket regression and reasoning quality are TBD until Month 1 baseline data is available.
- **Disqualification rule unit tests** are tenant-specific and cannot be finalized until tenant onboarding configures the per-tenant rules.
- **E2E environment** (staging vs local Docker compose) not decided. Decide before Sprint 2 begins.

## Follow-up Questions

- Which Python testing framework does the team prefer? (pytest is standard; confirm before scaffolding test directories)
- Should E2E tests run against a dedicated staging environment or a local Docker compose stack?
- Is there a budget cap for LLM evaluation suite runs per PR, or should evaluation only trigger on prompt/signal/model change PRs?
