---
type: analysis
question: "Which steps in the Lead Intelligence Engine workflow are automation, agent-driven, or hybrid?"
date: 2026-04-26
tags: [classification, automation, agent, hybrid, architecture, workflow, execution-type]
sources_consulted:
  - "[[concepts/agent-vs-tool-classification]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/lead-pipeline-architecture]]"
  - "[[analyses/governance-observability-layer]]"
status: COMPLETE
---

# Workflow Step Execution Type Classification

**Question:** Which steps in the Lead Intelligence Engine workflow are automation, agent-driven, or hybrid?  
**Date:** 2026-04-26

---

## Classification Framework

Three execution types. Every workflow step maps to exactly one.

| Type | Definition | Decision authority | Cost profile |
|---|---|---|---|
| **AUTOMATION** | Deterministic, rule-based logic. Same input always produces same output. No LLM involved. | Code | Cheap, fast, debuggable |
| **AGENT** | LLM reasoning is the primary and authoritative output. No deterministic rule overrides or materially constrains the LLM's output after the fact. | LLM | Expensive, variable, non-deterministic |
| **HYBRID** | A single step that internally combines LLM judgment with deterministic computation — and where the deterministic logic can materially override or constrain the LLM's output as part of the same atomic operation. | LLM + Code | Variable (LLM cost + deterministic enforcement) |

**The hybrid boundary:** A step is HYBRID only when LLM reasoning and deterministic enforcement are bound together inside one callable unit — not merely adjacent in the pipeline. An AGENT step followed by a separate TOOL validation step is two steps, not one hybrid step. The distinction matters: HYBRID means the deterministic rules can override the LLM's answer within the same call, before the result leaves that component.

**What this is not:** This document does not re-classify the LLM_AGENT / TOOL split from [[concepts/agent-vs-tool-classification]]. That document classifies components by whether they use an LLM. This document classifies workflow steps by execution type — a finer-grained view that identifies the HYBRID pattern and makes the deterministic/LLM boundaries explicit for developers.

---

## Summary: All Steps at a Glance

### Pipeline 2 — Onboarding (Once Per Tenant)

| # | Step | Execution Type | Notes |
|---|---|---|---|
| P2-1 | Tenant info intake | HYBRID | Structured form collection (AUTOMATION) + LLM-assisted clarification and strengthening of inputs before passing to Onboarding Agent |
| P2-2 | Onboarding Agent | AGENT | LLM interprets open-ended business description into structured PersonaObject |
| P2-3 | ICP Agent | AGENT | LLM reasons from persona to define ideal customer profile |
| P2-4 | Signal Agent | AGENT | LLM decides which signals are relevant per dimension and how many |
| P2-5 | Prompt Template Generation | AUTOMATION | Orchestrator mechanically converts signal names into template slots |

### Pipeline 1 — Pre-Run Setup (Per Run)

| # | Step | Execution Type | Notes |
|---|---|---|---|
| P1-0a | Event/Trigger Intake | AUTOMATION | Chat classification, scheduled timer, or webhook receipt |
| P1-0b | Intent Classification | AUTOMATION | Rule/small-model mapping; not a full LLM call |
| P1-0c | Pre-flight Validation | AUTOMATION | Checks onboarding_complete, signal defs, prompt template present |
| P1-0d | Context Loading | AUTOMATION | DB fetches: tenant_config, persona, signal_definitions, prompt_template |
| P1-0e | Capability Registry Resolution | AUTOMATION | Loads tool sequence for this use case; zero orchestrator code changes per new use case |
| P1-0f | Run ID Generation | AUTOMATION | UUID generation; establishes scope for all lineage writes in this run |

### Pipeline 1 — Per-Lead Parallel Processing

| # | Step | Execution Type | Notes |
|---|---|---|---|
| P1-1 | Data Gather | AUTOMATION | Parallel channel connector calls, deduplication, rate limiting |
| P1-2a | Lead Enrichment — Data Collection | AUTOMATION | CRM lookup, web/social data, chat transcripts, past orders; internal sources before external |
| P1-2b | Lead Enrichment — Signal Extraction | AUTOMATION | Deterministic evaluation of detection_rules against collected data; no LLM |
| P1-3 | Normalise | AUTOMATION | Schema transform, E.164 phones, ISO-8601 dates, city-tier mapping, data completeness scoring, conflict resolution |
| P1-4 | Prompt Template Fill | AUTOMATION | Mechanical: inserts extracted signal values into template slots; no interpretation |
| **P1-5** | **Scoring** | **HYBRID** | LLM call (Rating Agent) + banding enforcement (Output Schema Layer); see detail below |
| P1-6 | Disqualification Gate | AUTOMATION | Static business rules: geo cap, role penalty, spam/student force-zero |
| P1-7 | Bucketize | AUTOMATION | Threshold comparison: score ≥ 80 → HOT, ≥ 55 → WARM, < 55 → COLD |
| P1-8 | Lead Completeness Routing | AUTOMATION | Reads `needs_review` flag set by Output Schema Layer; routes to human_review queue if true |
| P1-9 | Delivery Handoff | AUTOMATION | Passes bucketed leads to Delivery and Integration Layer; no scoring logic |

### Governance & Background Jobs

| # | Step | Execution Type | Notes |
|---|---|---|---|
| G-1 | Lineage Writes | AUTOMATION | pipeline_run + task_execution + lineage_record; written by orchestrator after every stage |
| G-2 | SLA Tracker | AUTOMATION | Time-based: HOT 24h, WARM 2-3d, COLD weekly; breach → alert |
| G-3 | Score Decay Job | AUTOMATION | Scheduled: −10 pts/7d, −20 pts/14d, auto-COLD/30d |
| G-4 | Feedback Collector | AUTOMATION | Ingests thumbs up/down, outcomes, CRM status updates |
| G-5 | Quality Metrics — Per-Run SQL | AUTOMATION | Score Coverage, completeness distribution, bucket distribution, failure rates |
| G-6 | Quality Metrics — Weekly SQL | AUTOMATION | AR1–AR4, C1 Bucket Stability, C2 Score Drift |
| G-7 | Quality Metrics — Monthly SQL | AUTOMATION | AP1–AP3, C4 Decay Coherence, AR5 Priority Alignment |
| G-8 | Pattern Detection | AUTOMATION | SQL grouping by signal_version, prompt_version, fired_signals; count-based threshold |
| G-9 | Team Lead Recommendation Delivery | AUTOMATION¹ | Templated recommendation message to team_lead role |
| **G-10** | **Proactive Business Check-In** | **HYBRID²** | Templated outreach (AUTOMATION) + natural language response classification (classifier); see detail below |
| G-11 | Pipeline 2 Re-run | AGENT (via P2) | Triggers Onboarding/ICP/Signal Agents when team lead approves; routes to Pipeline 2 steps P2-2 through P2-5 |

¹ May become HYBRID if LLM-generated recommendation wording is introduced. Currently templated.  
² Execution type of the response interpretation step (classifier) is not fully locked — see Open Questions.

---

## Detailed Step Breakdown

---

### Pipeline 2 — Onboarding

#### P2-1 — Tenant Info Intake `HYBRID`

Collects the tenant's business description and uses LLM assistance to strengthen the inputs before they are passed to the Onboarding Agent.

**Component A — Structured intake (AUTOMATION)**

A guided form or conversational questionnaire collects the tenant's core business information: business type, industry, target roles, company size, sales cycle, geography focus, product lines, and any negative profiles (who to exclude). This part is deterministic — known fields, known schema.

**Component B — LLM-assisted strengthening (AGENT component)**

Before the raw inputs are passed to the Onboarding Agent, an LLM reviews the answers and helps make them more complete and precise — for example, prompting for missing detail, clarifying ambiguous answers, or surfacing unstated assumptions (e.g., "you mentioned B2B but haven't described your typical buyer's decision-making structure — can you add that?"). This ensures the Onboarding Agent receives a richer, more explicit description rather than a sparse or vague one.

**Why HYBRID and not pure AGENT:** The LLM is not producing the persona here — it is augmenting structured inputs. The intake form provides the deterministic scaffold; the LLM strengthens the content within that scaffold. The Onboarding Agent (P2-2) remains the step that produces the structured PersonaObject.

**Why this matters:** The quality of the PersonaObject, ICP, and signal definitions produced by Pipeline 2 depends directly on how rich and explicit the tenant's initial description is. An LLM-assisted intake reduces the risk of a sparse or misleading persona — which would silently degrade every lead score this tenant ever produces.

---

#### P2-2 — Onboarding Agent `AGENT`

**Input:** Raw tenant business description  
**Output:** Structured `PersonaObject` (business_type, target_roles, company_size, sales_cycle, ticket_size, geography_focus, product_lines, negative_profiles)

The LLM's judgment is the output. The Onboarding Agent must interpret open-ended, free-text business descriptions — a task that cannot be reduced to rules because every tenant's description is different.

**Why not HYBRID:** The orchestrator validates the PersonaObject for required fields and weight sums after receiving it, but this validation is a separate downstream step (Pre-flight Validation) — not bundled inside the Onboarding Agent call itself. The agent produces the output; the orchestrator checks it separately.

**Why not AUTOMATION:** The input (business description) is unstructured. No static rule can map "we sell industrial HVAC systems to procurement managers at mid-market factories" → a PersonaObject. Requires language understanding.

---

#### P2-3 — ICP Agent `AGENT`

**Input:** PersonaObject  
**Output:** `IcpDefinition` — target segment, priority signals, disqualifying signals, buying triggers, ICP examples

Defines who the ideal customer is. Requires reasoning from the persona to project what an ideal buyer looks like — a task requiring judgment, not rule application.

**Stored as:** `ideal_customer_profile` entity (S1) and as `icp: IcpDefinition` inside the PersonaObject.  
**Versioned:** Every ICP snapshot stored in `ideal_customer_profile_version` — historical scores can identify which ICP was active.

---

#### P2-4 — Signal Agent `AGENT`

**Input:** PersonaObject + IcpDefinition  
**Output:** Set of `signal` records — one per scoring question, across five dimensions (Fit, Intent, Engagement, Behaviour, Context)

The Signal Agent decides:
- Which signals are relevant to this tenant's business and ICP
- How many signals are needed per dimension (Intent: 5+, Engagement: 6+, others TBD)
- What each signal's name, description, detection_rule, and weight_within_dimension should be

This is domain-specific, creative, and tenant-specific. No rule can enumerate the right signals for every possible business type.

**Why signal extraction in Pipeline 1 is AUTOMATION, not AGENT:** The Signal Agent defines *what to look for* (once, at onboarding). Lead Enrichment evaluates *whether it was found* (per lead, deterministically using the detection_rule). The intelligence is front-loaded into the signal definition; execution is deterministic.

---

#### P2-5 — Prompt Template Generation `AUTOMATION`

**Input:** Signal definitions from Signal Agent  
**Output:** Prompt template with one named slot per signal, stored in `prompt_registry`

The orchestrator mechanically maps each signal's `name` to a `{slot_name}` placeholder in a fixed template structure. No reasoning — pure string assembly. The scoring rubric (static part, system message) and slot structure (dynamic part, user message) are pre-defined. The orchestrator inserts the slot names.

---

### Pipeline 1 — Per-Run Setup

#### P1-0a — Event/Trigger Intake `AUTOMATION`

Three trigger types are handled deterministically:
- **Interactive (chat):** Message received from salesperson → extract user_id, tenant_id → pass to intent classifier
- **Scheduled:** Timer fires → load run params from schedule config
- **Webhook:** Inbound lead event from channel → parse payload → queue for processing

No reasoning. Pure event routing.

---

#### P1-0b — Intent Classification `AUTOMATION`

For interactive triggers: maps the salesperson's message to one of a small set of known intents (score leads, check lead status, view ranked list, etc.).

**Classification from [[concepts/agent-vs-tool-classification]]:** TOOL — "rule/small-model mapping." This is not a full LLM call. The intent space is bounded and known. If the intent is ambiguous, the orchestrator presents 2-3 options to the salesperson and waits — it does not guess.

---

#### P1-0c — Pre-flight Validation `AUTOMATION`

Before any leads are touched, the orchestrator validates three conditions:
1. `tenant.onboarding_complete = true`
2. Signal definitions exist for this tenant
3. Prompt template exists for this tenant and use case

If any condition fails: HALT and tell the user what is missing. No partial runs.

---

#### P1-0d — Context Loading `AUTOMATION`

DB fetches — no computation:
- `tenant_config` (concurrency cap, LLM model, token budget, per-tenant limits)
- `persona` object (business profile, scoring weights, banding thresholds)
- `signal_definitions` (the full list of signals this tenant uses)
- `prompt_template` (current active version from `prompt_registry`)

The Persona Engine caches the PersonaObject with a 15-minute TTL to avoid redundant DB reads during batch runs.

---

#### P1-0e — Capability Registry Resolution `AUTOMATION`

Loads the tool sequence for this use case:

```
use_case: lead_enrichment
tools: [data_gather, lead_enrichment, normalise, scoring_agent, bucketize]
```

Zero orchestrator code changes per new use case — new use cases add a registry entry. The registry maps use case → ordered tool list. Resolution is a lookup, not reasoning.

---

### Pipeline 1 — Per-Lead Parallel Processing

#### P1-1 — Data Gather `AUTOMATION`

Fetches all new leads from every channel the tenant has connected. All channels called in parallel.

**Deterministic components:**
- Per-tenant rate limits enforced per channel connector
- Deduplication: phone first → email second → name + location fallback
- Failure isolation: one failed channel logs and continues; all channels failed halts the run

**Why not AGENT:** No reasoning about leads. Pure data retrieval and deduplication.

---

#### P1-2a — Lead Enrichment: Data Collection `AUTOMATION`

Gathers additional information about each lead from available sources:
- Website visit history
- Social profiles
- Company data
- Internal CRM records
- Chat transcripts
- Past orders
- External news

Rule: internal sources before external lookups. No LLM involved — pure connector calls and data aggregation.

---

#### P1-2b — Lead Enrichment: Signal Extraction `AUTOMATION`

For each signal defined in P2-4, the orchestrator runs the `detection_rule` against the collected data and extracts a value:

```
{pricing_request}    → true
{demo_requested}     → false
{urgency_language}   → true
{response_speed}     → "fast"
{revisit_count}      → 3
```

This is fully deterministic. The `detection_rule` format is now locked — see [[analyses/signal-detection-rule-spec]]. Format: `{ type, source_fields, params }` using a named-extractor vocabulary. Execution uses a strategy-pattern registry; given the same data, extraction always produces the same values. This is not an LLM call.

**Why this step is separated from Scoring:** Keeping extraction deterministic means scoring errors and extraction errors are independently debuggable. If a lead gets a wrong bucket, you can inspect the extracted signal values to determine whether the error was in extraction (wrong values) or scoring (wrong judgment from correct values).

---

#### P1-3 — Normalise `AUTOMATION`

Standardises all lead data before it goes to the Scoring Agent:

| What | Rule |
|---|---|
| Phone numbers | E.164 format (`+91XXXXXXXXXX`) |
| Names | Title Case, no emojis |
| Locations | city + state + country + tier (1 / 2 / 3) |
| Dates | ISO 8601 UTC |
| Product interest | Internal taxonomy mapping `[TBD per tenant]` |

Also assigns a **data completeness score** (0–100%) based on how many expected fields are populated and verified. This score is injected into the prompt at P1-4 and becomes the `lead_completeness` field in ScoringOutput.

**Conflict resolution:** most recent data wins for contact details; CRM data overrides self-reported; unresolvable conflicts → store both, flag for review, log the conflict. All rules, no judgment.

---

#### P1-4 — Prompt Template Fill `AUTOMATION`

Inserts the signal values extracted in P1-2b into the template slots from P2-5:

```
{pricing_request}  →  pricing_request : true
{response_speed}   →  response_speed : fast
{revisit_count}    →  revisit_count : 3
```

Also injects the completeness score from P1-3. The result is the fully assembled prompt passed to the Scoring Agent. No reasoning — pure slot substitution.

---

#### P1-5 — Scoring `HYBRID`

This is the only HYBRID step in the Pipeline 1 critical path. It contains two tightly bound components that execute atomically within the single `score_lead()` call:

**Component A — Rating Agent (LLM)**

Makes exactly one logical LLM call. The filled prompt from P1-4 is passed with the tenant's PersonaObject and ICP definition. The LLM produces:

```json
{
  "score": 84,
  "bucket": "hot",
  "reasoning": "Strong ICP fit, explicit pricing + timeline signals, multi-channel active lead",
  "lead_completeness": 0.87,
  "sub_scores": { "fit": 21, "intent": 22, "engagement": 17, "recency": 15 },
  "recommended_action": "Call today",
  "needs_review": false,
  "schema_version": "v1.0",
  "prompt_version": "v1.3.0",
  "model": "gpt-4o"
}
```

Hard timeout: 30 seconds (LLM call budget within the 60-second layer timeout).

**Component B — Output Schema Layer (AUTOMATION)**

Processes the LLM output deterministically:

| Operation | What happens | Why deterministic wins |
|---|---|---|
| Schema validation | Validates JSON against canonical ScoringOutput schema | Malformed output is never passed downstream |
| Coercion | Case normalisation, score rounding, whitespace trimming | Minor inconsistencies corrected by rule |
| **Banding enforcement** | **If LLM bucket disagrees with `score + tenant banding rules`, banding wins.** Discrepancy is logged. | Tenant-configured thresholds (80/55/0) are authoritative — LLM cannot override them |
| Lead completeness gate | If `lead_completeness` < configured threshold → `needs_review = true` | Deterministic threshold check, not LLM judgment |
| Schema version recording | Records schema_version on every output | Enables rollback and audit |

**Why this step is HYBRID and not AGENT:**

The LLM's output is not final. The Output Schema Layer enforces deterministic banding rules that **can and do override the LLM's bucket**. If the LLM returns `bucket: "hot"` for a lead that scored 72, the Output Schema Layer overwrites it to `"warm"` (HOT threshold is 80). The LLM's judgment operates within bounds set by deterministic rules. This is the defining characteristic of a HYBRID step.

**Why the components are not split into two separate steps:**

Both components are internal to the Intelligence Layer's `score_lead()` function. The Orchestration Layer sees only a single call with a typed return: `ScoringOutput | ScoringFailure`. The orchestrator cannot invoke them separately. They are one atomic unit.

**Failure handling (within the HYBRID step):**

| Failure mode | Response |
|---|---|
| Malformed JSON | Retry once with schema reminder appended to prompt |
| Schema mismatch | Retry once |
| Timeout | Retry once with extended deadline |
| Rate limit | Wait for rate limit window, retry once |
| Two consecutive failures | ScoringFailure returned → lead routed to human_review |

---

#### P1-6 — Disqualification Gate `AUTOMATION`

Applies static business rules that override the score from P1-5. Runs after scoring, before bucketize.

| Condition | Override |
|---|---|
| Outside serviceable area | Score capped at 50, or marked disqualified |
| Wrong geography | −30 points |
| Non-decision-maker | −40 points |
| Student / spam / clearly irrelevant | Score forced to 0 |

Exact rules are `[TBD per tenant]` — configured at onboarding. The execution is deterministic: check condition → apply penalty → no judgment.

**Note:** The Disqualification Gate applies a different kind of deterministic override than the Output Schema Layer's banding. The Output Schema Layer enforces the LLM's own bucket against the score (intra-step). The Disqualification Gate applies hard business rules from outside the LLM's reasoning (post-step). These are complementary, not redundant.

---

#### P1-7 — Bucketize `AUTOMATION`

Reads the final score (after disqualification adjustments) and assigns a bucket:

| Bucket | Score range | SLA |
|---|---|---|
| HOT | 80–100 | 24 hours |
| WARM | 55–79 | 2–3 days |
| COLD | 0–54 | Weekly nurture |

Thresholds are tenant-configurable starting points (80/55/0). Pure threshold comparison — no reasoning.

---

#### P1-8 — Lead Completeness Routing `AUTOMATION`

Reads the `needs_review` flag set by the Output Schema Layer in P1-5. If `needs_review = true`, the lead's `pipeline_stage` is set to `human_review`. If `false`, it proceeds to `delivered`.

This is not a new evaluation — it is applying the decision already made by the Output Schema Layer inside P1-5. The routing step is a deterministic branch on a pre-computed boolean.

**Human review queue:** There is no separate table. `pipeline_stage = 'human_review'` is a filtered view of the `leads` table.

---

#### P1-9 — Delivery Handoff `AUTOMATION`

Passes the bucketed, scored leads to the Delivery and Integration Layer. The orchestrator sets `pipeline_stage = 'delivered'` and writes the final lineage record. From this point, delivery failures (CRM sync errors, notification failures) never roll back Pipeline 1 — the score is already persisted.

Full delivery spec: [[analyses/delivery-integration-layer]]

---

### Governance & Background Jobs

#### G-1 — Lineage Writes `AUTOMATION`

After every tool call, at every stage, in both pipelines, the orchestrator writes three entity records:

| Entity | Answers |
|---|---|
| `pipeline_run` | Did the whole run succeed? |
| `task_execution` | Which stage failed, how long did it take, how many retries? |
| `lineage_record` | What input went in, what output came out, which prompt version was used? |

Write order is locked: `lineage_record` → `task_execution` → `pipeline_run` → `leads.pipeline_stage` (always last). This is the crash safety guarantee.

Lineage is the foundation for the entire quality metrics system. All 15 quality metrics and 3 Global KPIs trace back to lineage fields.

---

#### G-2 — SLA Tracker `AUTOMATION`

Background job. Monitors time elapsed since `pipeline_stage = 'delivered'` for each lead. On breach: dispatches alert to team lead (channel TBD). SLA windows: HOT 24h, WARM 2-3d, COLD weekly.

---

#### G-3 — Score Decay Job `AUTOMATION`

Scheduled background job. Reduces scores on inactive leads: −10 pts at 7 days, −20 pts at 14 days, auto-COLD at 30 days. Coherence tracked by quality metric C4 (Decay-Rescore Coherence).

---

#### G-4 — Feedback Collector `AUTOMATION`

Ingests feedback events from the Delivery Layer: thumbs up/down ratings, CRM outcome updates (responded, meeting booked, qualified, deal closed), salesperson notes. Writes to `feedback_record` entity. No interpretation — pure event ingestion.

---

#### G-5 / G-6 / G-7 — Quality Metrics SQL Jobs `AUTOMATION`

Three cadences, all deterministic SQL against existing Postgres tables. No LLM involved.

| Cadence | Trigger | Metrics |
|---|---|---|
| Per-run | End of every Pipeline 1 run | Score Coverage Rate, completeness bands, bucket distribution, failure rate, human review rate |
| Weekly | Monday 00:00 | AR1 SLA Compliance, AR2 Action Rate, AR3 Time-to-Action, AR4 Action Types, C1 Bucket Stability, C2 Score Drift |
| Monthly | Month-end (min 100 outcomes/bucket) | AP1 Bucket Outcome Rate, AP2 Discrimination Ratio, AP3 Completeness Qualifier, C4 Decay-Rescore Coherence, AR5 Priority Alignment |

Results written to `quality_snapshots`. Dashboard queries read only from `quality_snapshots` — never from raw pipeline tables (no read/write contention).

---

#### G-8 — Pattern Detection `AUTOMATION`

Feedback loop Step 2. Weekly SQL job groups attributed_feedback records by `(signal_version, prompt_version, fired_signals, explanation_reasons)` and counts occurrences. If a pattern exceeds a fixed-count threshold N `[TBD — set after Month 1]`, it is flagged for team lead review.

Detection is pure SQL aggregation. The threshold comparison is deterministic. No LLM reasoning involved in deciding whether a pattern is significant.

---

#### G-9 — Team Lead Recommendation Delivery `AUTOMATION`

Feedback loop Step 3. When G-8 flags a pattern, the system formulates a recommendation and routes it to the team_lead role for that tenant. The recommendation identifies: which signal/prompt version pattern triggered it, and which action options are available (re-run ICP + Signal Agent, adjust weight manually, update prompt template, investigate, dismiss).

**Currently:** templated recommendation from detected pattern fields. No LLM.  
**Possible future state:** LLM-generated explanation of the pattern — would shift to HYBRID. See Open Questions.

**Rule: system proposes, team lead approves. Never automated.** `[LOCKED principle]`

---

#### G-10 — Proactive Business Check-In `HYBRID`

Scheduled outreach to the tenant's team lead to ask whether anything significant has changed in the business (new market, new customer type, new product focus).

**Component A — Outreach (AUTOMATION)**

System sends a templated chat message to the team_lead on a recurring schedule `[TBD: 2-week or monthly cadence]`. The message is templated, not LLM-generated.

**Component B — Response Classification (classifier, type TBD)**

The team lead's natural language response is classified into one of three outcomes:
- No change → no action
- Minor update → update specific config fields
- Significant change → propose Pipeline 2 re-run (ICP + Signal Agents) for team lead approval

The classification of an unstructured response into these categories requires some form of language understanding. The current design tags this as TOOL ("rule/small-model mapping") in [[concepts/agent-vs-tool-classification]] — but whether it is a simple rule set or requires an LLM classifier is `[TBD]`.

**Why HYBRID:** Both AUTOMATION (scheduled templated outreach) and at least a classifier-level language model (response interpretation) combine in a single step. If the classifier is a full LLM call, this becomes a more clearly HYBRID step.

**If classification is a rules-based classifier only:** This step is AUTOMATION.  
**If classification is an LLM call:** This step is HYBRID (LLM response classification + deterministic routing of the outcome).

---

#### G-11 — Pipeline 2 Re-run `AGENT (via Pipeline 2)`

When the team lead approves a re-run recommendation (from G-9 or G-10), the orchestrator triggers Pipeline 2 steps P2-3 (ICP Agent) and P2-4 (Signal Agent) with the updated context. Full Pipeline 2 is only re-run for major persona changes.

This routes back to the AGENT steps in Pipeline 2. The approval step itself (team lead pressing approve) is a human action, not a system step.

---

## Why These Hybrid Boundaries

### The Scoring Step Boundary (P1-5)

The Scoring step is the most architecturally important hybrid in the system. The boundary is drawn here because:

1. **The banding enforcement overrides LLM output within the same call.** The Output Schema Layer is not a separate validation step — it is an internal component of `score_lead()`. The Orchestration Layer cannot invoke Rating Agent and Output Schema Layer independently.

2. **The deterministic component materially changes the output.** If the LLM returns an incorrect bucket, the Output Schema Layer silently corrects it. This is not cosmetic coercion (trimming whitespace) — it is an authoritative override of the LLM's judgment using tenant-configured rules.

3. **The hybrid classification enables correct testing.** Treating Scoring as HYBRID means it needs two test strategies: unit tests for the Output Schema Layer (deterministic — always same output) and evaluation suites for the Rating Agent (statistical — distribution of outputs across leads). Treating it as pure AGENT would suggest evaluation-only testing, which would miss banding bugs. Treating it as pure AUTOMATION would be wrong.

### Why the Tenant Intake Is Hybrid But the Pipeline 2 Agents Are Not

**P2-1 (Tenant Intake) is HYBRID** because it combines a structured form scaffold (AUTOMATION) with LLM-assisted strengthening of the tenant's inputs (AGENT component) — both operating on the same data before it leaves the step. The LLM is not producing the persona; it is improving the raw material that the Onboarding Agent will use.

**P2-2, P2-3, P2-4 (Onboarding, ICP, Signal Agents) are AGENT** because their output is the direct product of LLM reasoning with no deterministic rules that materially override or constrain that output within the same call. The orchestrator validates the PersonaObject (weights sum to 100, required fields present) after receiving it — but that validation is a separate downstream orchestration step, not bundled inside the agent call itself. This is (AGENT → AUTOMATION), not one HYBRID step.

### Why Signal Extraction Is Automation (Not Hybrid)

Signal extraction uses `detection_rules` defined by the Signal Agent (AGENT) to evaluate lead data. The output of the Signal Agent (signal definitions) informs what the detection_rules look for — but the detection_rule evaluation itself is deterministic. An LLM defined the rules once; a deterministic evaluator applies them per lead. This is the correct architecture: intelligence front-loaded into rule design, execution kept cheap and debuggable.

---

## Open Questions

1. **Proactive check-in classifier (G-10):** Is the response classification a rule-based system or an LLM call? This determines whether G-10 is AUTOMATION or HYBRID. The current design tags the intent classifier as TOOL. If this holds, G-10 becomes AUTOMATION. **Owner: team decision.**

2. **Team lead recommendation wording (G-9):** Should the recommendation message to the team lead be LLM-generated (explaining the detected pattern in plain English) or templated (pattern fields inserted into a fixed format)? If LLM-generated, G-9 shifts from AUTOMATION to HYBRID. **Owner: team decision.**

3. **Signal detection_rule format (P1-2b):** **RESOLVED 2026-04-28.** Named extractor + params model. Fully deterministic — no LLM call in extraction. P1-2b AUTOMATION classification is protected. 1-LLM-call-per-lead guarantee preserved. See [[analyses/signal-detection-rule-spec]].

4. **Disqualification rule configuration (P1-6):** Disqualification rules are tenant-defined at onboarding. If rules can include free-text conditions interpreted by the LLM, the Disqualification Gate shifts from AUTOMATION to HYBRID. Design intent is static rules only. **Owner: to be locked at tenant onboarding spec.**

---

## Design Implications

| Implication | Detail |
|---|---|
| **Test strategy** | AUTOMATION steps → unit tests (deterministic input/output). AGENT steps → evaluation suites (statistical quality across representative leads). HYBRID steps → both: unit tests for the deterministic component, evaluation for the LLM component |
| **Debugging** | When a lead gets a wrong bucket: check extracted signal values first (P1-2b — AUTOMATION bug) before checking scoring judgment (P1-5 — LLM/HYBRID issue). Separation makes blame assignment fast. |
| **Cost attribution** | Only AGENT and HYBRID steps incur LLM costs. Pipeline 2 AGENT steps: 3 LLM calls per tenant onboarding (one-time). Pipeline 1 HYBRID step: 1 LLM call per lead. All other steps: no LLM cost. |
| **Retry policy** | AUTOMATION steps: 1 retry → fail. AGENT steps in Pipeline 2: 1 retry → halt onboarding, alert admin. HYBRID step (Scoring): failure table in orchestration-layer-spec Section 4.3 Stage 4 — up to 2 retries with mode-specific handling. |
| **Observability** | HYBRID and AGENT steps emit extended observability signals: `prompt_version`, `model`, `tokens_in`, `tokens_out`, `latency_ms`, `schema_validation_result`. AUTOMATION steps emit: `duration_ms`, `status`, `retry_count`. |

---

## Follow-up Questions

1. Lock the proactive check-in intent classifier as rule-based or LLM — this changes G-10's execution type.
2. Lock the team lead recommendation wording as templated or LLM-generated — this changes G-9's execution type.
3. ~~Lock `signal.detection_rule` format~~ — **RESOLVED 2026-04-28.** Locked as fully deterministic named-extractor model. P1-2b AUTOMATION classification confirmed. See [[analyses/signal-detection-rule-spec]].
