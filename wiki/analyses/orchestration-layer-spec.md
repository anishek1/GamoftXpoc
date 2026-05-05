---
type: analysis
question: "Document orchestration controller, tool invocation, and state tracking responsibilities."
date: 2026-04-19
tags: [orchestration, system-layer, subtask-3, spec, controller, state-tracking, tool-invocation, two-pipeline]
sources_consulted: [sources/2026-lead-intelligence-engine-reference, raw/assets/lead_intelligence_manual_enrichment_playbook, sources/2026-intelligence-layer-design, sources/2026-core-business-entities]
related: [analyses/orchestration-layer-dependencies, analyses/governance-observability-layer]
last_updated: 2026-05-03
status: COMPLETE — updated 2026-05-03 to reconcile with global-data-collection-architecture, meta-integration-implementation, and meta-platform-api-deep-research; 6 problems fixed, 3 cross-references added
---

# S3 — Orchestration Layer

**Deliverable:** Subtask 3 — Orchestration Controller, Tool Invocation, State Tracking
**Audience:** S1 (data layer) and S2 (intelligence layer) developers
**Date:** 2026-04-19

---

## 1. What Is the Orchestration Layer?

The orchestration layer is the engine that runs everything — but it never makes any AI decisions itself. It is a **deterministic controller**: it decides the order of operations, calls the right tools at the right time, handles failures, and tracks where every lead is at every moment.

Every pipeline starts from the orchestrator. Every tool is called by the orchestrator. Every state update is written by the orchestrator.

**What it is not:** it does not contain any scoring logic, persona logic, or signal logic. Those live in the agents (S2). It does not own the database schemas. Those live in the data layer (S1). The orchestrator just runs the sequence.

---

## 2. System Architecture

```
                     ┌─────────────────────────────┐
                     │        ORCHESTRATOR          │
                     │     (deterministic only)     │
                     └──────────────┬──────────────┘
                                    │
               ┌────────────────────┴───────────────────┐
               │                                        │
               ▼                                        ▼
  ┌─────────────────────────┐         ┌──────────────────────────────┐
  │   PIPELINE 2            │         │   PIPELINE 1                 │
  │   Onboarding            │         │   Lead Processing            │
  │   (once per tenant)     │         │   (every time leads run)     │
  │                         │         │                              │
  │  Onboarding Agent (LLM) │         │   Data Gather (channels)     │
  │          ↓              │         │          ↓                   │
  │  ICP Agent (LLM)        │────────►│   [DM] Pre-Filter Gate       │
  │          ↓              │  signal │   [DM] Msg Parser / Haiku    │
  │  Signal Agent (LLM)     │  defs + │   [Lead Ad] joins at ▼       │
  │          ↓              │  prompt │   Lead Enrichment            │
  │  Prompt Template built  │         │   + Consent Gate             │
  └─────────────────────────┘         │          ↓                   │
          │ lineage                   │   Normalise                  │
          │ writes                    │          ↓                   │
          │ (both pipelines)          │   Intent Gate                │
          └──────────────────────────►│   ↓         ↓ await_clarif.  │
                                      │   Scoring Agent (Sonnet)     │
                                      │          ↓                   │
                                      │   Bucketize                  │
                                      └──────────────┬───────────────┘
                                           lineage   │ scored leads
                                           writes    │ (Pipeline 1 only)
                                                     │
              ┌──────────────────────────────────────▼───────────────┐
              │       DELIVERY AND INTEGRATION LAYER                  │
              │                                                       │
              │  Chat (lead cards) · Notifications · Dashboards      │
              │  CRM Sync · External API + Webhooks · Reports        │
              │  → [[analyses/delivery-integration-layer]]           │
              └──────────────────────────────────────────────────────┘
                         │ feedback signals (thumbs up/down, outcomes)
                         ▼
              ┌─────────────────────────────────────────────────────┐
              │                GOVERNANCE LAYER                       │
              │   monitoring · auditability · feedback loops          │
              │   lineage (pipeline_log) · security                   │
              │                                                       │
              │   ┌─────────────────────────────────────────────┐     │
              │   │          QUALITY TRACKING                   │     │
              │   │   [[analyses/scoring-quality-metrics]]      │     │
              │   │                                             │     │
              │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │     │
              │   │  │ PER-RUN  │  │  WEEKLY  │  │ MONTHLY  │   │     │
              │   │  │ Coverage │  │ AR1 SLA  │  │ AP1 BOR  │   │     │
              │   │  │ Confid.  │  │ AR2 Act  │  │ AP2 Sep  │   │     │
              │   │  │ Buckets  │  │ C1 Stab  │  │ AP3/C4   │   │     │
              │   │  │ Failures │  │ C2 Drift │  │ AR5 Algn │   │     │
              │   │  └────┬─────┘  └────┬─────┘  └────┬─────┘   │     │
              │   │       └─────────────┼──────────────┘        │     │
              │   │                     ▼                       │     │
              │   │           quality_snapshots                 │     │
              │   │                     │                       │     │ 
              │   │        ┌────────────┼───────────┐           │     │ 
              │   │        ▼            ▼           ▼           │     │
              │   │    System       Business     Tenant         │     │
              │   │    Health       Health       Health         │     │ 
              │   │    (weekly)     (monthly)    Rate           │     │ 
              │   └─────────────────────────────────────────────┘     │
              │                        │                              │
              │           team lead + product owner review            │
              │           → recalibrate buckets (AP1 / AP2)           │
              │           → update weights / approve Pipeline 2       │
              └──────────────────────────────────────────────────────┘
                                        │ config applied to next run
                                        ▼
                                   ORCHESTRATOR
```

**Two points to read this diagram correctly:**

1. **Pipeline 2 does not feed the Delivery and Integration Layer.** Pipeline 2's outputs (personas, signal_definitions, prompt_registry) go only to internal data stores. Only Pipeline 1's scored leads flow to the Delivery and Integration Layer, after Bucketize completes.

2. **There are two distinct integration layers in the system — they are not the same thing:**
   - **Channel Integration Layer** (upstream of Pipeline 1) — how tenant platforms connect to the system and how lead events enter Pipeline 1. WhatsApp DMs, Meta Lead Ads, LinkedIn, and website forms all enter here via OAuth and webhooks. Documented in [[analyses/channel-integration-layer]].
   - **Delivery and Integration Layer** (downstream of Pipeline 1, post-Bucketize) — how scored leads are delivered to salespeople, CRM systems, dashboards, and external APIs. Documented in [[analyses/delivery-integration-layer]].

**There are 4 LLM agents in the entire system:**

| Agent | Pipeline | What it does |
|---|---|---|
| Onboarding Agent | Pipeline 2 | Converts tenant business info into a structured persona |
| ICP Agent | Pipeline 2 | Defines what the ideal customer looks like for this tenant |
| Signal Agent | Pipeline 2 | Creates the signal definitions used to evaluate every lead |
| Scoring Agent | Pipeline 1 | Scores each lead using the signal values extracted from enrichment |

**LLM calls per lead — revised 2026-05-03:** The Scoring Agent (Sonnet) runs for every lead on both paths. On the DM path only, a second LLM call occurs earlier in the pipeline: the Message Parser (Haiku), which performs multilingual and typo-tolerant extraction from raw message text before signal extraction. Lead Ad events skip the Message Parser entirely and use only the Scoring Agent call. The three Pipeline 2 agents run once at onboarding. Signal extraction remains deterministic in all paths. Full detail: [[analyses/global-data-collection-architecture]] Sections 5 and 14.

---

## 3. Pipeline 2 — Tenant Onboarding (Runs Once)

Pipeline 2 sets up the intelligence that Pipeline 1 uses to score every lead. It runs once when a new tenant is onboarded. It only re-runs when the tenant's business profile changes significantly.

### 3.1 The Flow

```
Tenant answers questions about their business
                ↓
     Onboarding Agent (LLM)
     Creates a structured business persona
                ↓
         ICP Agent (LLM)
         Defines the ideal customer profile
                ↓
       Signal Agent (LLM)
       Creates signal definitions per scoring dimension
                ↓
     Orchestrator builds Prompt Template
     (one slot per signal, ready to be filled)
                ↓
     Everything stored → Pipeline 1 uses this for every lead
```

### 3.2 What Each Agent Produces

**Onboarding Agent → Business Persona**

The tenant describes their business. The Onboarding Agent structures it:

```
{
  tenant_id
  business_type        : B2B | B2C | Hybrid
  industry
  target_roles         : (B2B) e.g. "Procurement Manager, CTO"
  company_size         : Small | Mid | Enterprise
  sales_cycle          : Short | Medium | Long
  ticket_size          : Low | Medium | High
  decision_complexity  : Single-person | Multi-stakeholder
  geography_focus
  product_lines
  negative_profiles    : who to exclude (e.g. students, resellers)
}
```

Stored in: `personas` table

---

**ICP Agent → Ideal Customer Profile**

Using the persona, the ICP Agent defines who the best leads look like:

```
{
  tenant_id
  icp_description       : narrative of the ideal buyer
  target_segment        : industry, company size, geography, role profile
  priority_signals      : what to weight most (feeds into scoring_weights)
  disqualifying_signals : what eliminates a lead immediately (feeds into banding rules)
  buying_triggers       : events that signal readiness to buy
  icp_examples          : example leads (real or synthetic)
}
```

The ICP output is stored as the `ideal_customer_profile` entity in S1's data model and also captured inside the PersonaObject as the `icp: IcpDefinition` field — so the Persona Engine always has it available without a separate lookup. S1 also versions every ICP snapshot in `ideal_customer_profile_version`, which means when Pipeline 2 re-runs and produces a new ICP, the system can explain which ICP definition was active when any historical score was produced.

Stored in: `ideal_customer_profile` table (S1)

---

**Signal Agent → Signal Definitions**

Using both the persona and ICP, the Signal Agent creates the full list of signals across five dimensions:

| Dimension | Illustrative weight | What it captures |
|---|---|---|
| Fit | ~25% | Industry match, role match, serviceability, company size |
| Intent | ~30% | Price requests, demo requests, urgency language, timeline stated |
| Engagement | ~20% | Response speed, revisit count, multi-channel contact |
| Behaviour | ~15% | Past orders, prior proposals, payment patterns |
| Context | ~10% | Location, city tier, seasonality, external triggers |

Weights are per-tenant and configurable. These are illustrative starting points from the playbook.

Each signal is stored as:

```
{
  signal_id
  dimension            : fit | intent | engagement | behaviour | context
  name                 : "pricing_request"
  description          : "Lead explicitly asked for pricing or a quote"
  detection_rule       : { type, source_fields, params }  ← see [[analyses/signal-detection-rule-spec]]
  weight_within_dim    : float
  applicable_to        : B2B | B2C | both
}
```

S1 has formally confirmed `signal` and `signal_evaluation` as distinct data entities. `signal` stores the question (what to look for). `signal_evaluation` stores the per-lead answer (what was actually found). These are the data model backing the fill-in-the-blanks mechanism.

The `detection_rule` format is now locked — see [[analyses/signal-detection-rule-spec]]. Format: `{ type, source_fields, params }`. Execution uses a strategy-pattern registry of pre-built extractors. Every extractor returns `(detected: bool, value: float 0.0–1.0, evidence: str)`.

Stored in: `signal` table (S1 entity)

---

**Orchestrator → Prompt Template**

Once the signal definitions are ready, the orchestrator generates the prompt template. The template has one named slot for every signal. The slots get filled in by Lead Enrichment during Pipeline 1.

```
[Scoring instructions]
[Tenant persona injected]
[ICP definition injected]

Score this lead across 5 dimensions using the signal values below:

FIT SIGNALS:
  - {industry_match}   : {value}
  - {role_relevance}   : {value}

INTENT SIGNALS:
  - {pricing_request}  : {value}
  - {demo_requested}   : {value}
  - {urgency_language} : {value}

ENGAGEMENT SIGNALS:
  - {response_speed}   : {value}
  - {revisit_count}    : {value}

[...all signals across all dimensions...]

[Output format instruction — return JSON with bucket, score, breakdown, explanation, confidence]
```

Stored in: `prompt_registry` table (versioned)

### 3.3 When Pipeline 2 Re-Runs

Pipeline 2 is not automatic. Two events can trigger a re-run — both require the team lead to approve:

1. **Proactive check-in** — the system sends a chat message to the team lead on a recurring schedule (cadence TBD: 2 weeks or monthly) asking if anything has changed in the business. A significant change (new market, new customer type, new product focus) triggers a proposal to re-run ICP + Signal Agents.

2. **Feedback-driven** — the Governance Layer detects that a particular signal version or prompt version keeps producing wrong-bucket leads. The team lead gets a recommendation and can choose to re-run.

**Rule: the system proposes, the team lead approves. Never automatic.**

Full re-run mechanics: [[analyses/governance-observability-layer]] Sections 5.5 and 5.7

---

## 4. Pipeline 1 — Lead Processing (Runs Per Event)

Pipeline 1 runs whenever leads need to be scored. Every lead goes through six stages.

### 4.1 What Triggers a Run

| Trigger | How it works |
|---|---|
| Salesperson message in chat | "who should I call today?" → orchestrator classifies intent → confirms scope → runs |
| Scheduled run | Automated, no user interaction, runs on a set cadence |
| Webhook | New lead just arrived from a connected channel → run fires automatically |

**Two pipeline entry points — added 2026-05-03:** Not all leads enter Pipeline 1 at the same step. DM events (WhatsApp, Facebook Messenger, Instagram DM) enter at Step 0 (Pre-Filter Gate) and traverse the full pipeline including Message Parser. Lead Ad events (Facebook Lead Ads, Instagram Lead Ads) have already passed the channel-level filter and carry structured form data — they skip Steps 0–2 and enter at Step 3 (Jurisdiction Classifier). This means Lead Ads never hit the Message Parser. Full mapping: [[analyses/global-data-collection-architecture]] Section 14.

For interactive triggers: the orchestrator classifies the intent before doing anything. If the intent is ambiguous, it presents 2–3 options to the salesperson and waits. It never guesses.

### 4.2 The Pipeline Stages

```
                       TRIGGER (chat / schedule / webhook)
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │            DATA GATHER              │
                    │  WhatsApp DMs · FB/IG DMs           │
                    │  FB Lead Ads · IG Lead Ads          │
                    │  Website forms · LinkedIn · etc.    │
                    └───────────────┬─────────────────────┘
                                    │
               ┌────────────────────┴────────────────────────┐
               │ DM events (WhatsApp / FB / IG DM)           │ Lead Ad events
               ▼                                             │  (already structured)
    ┌───────────────────────┐                                │
    │   PRE-FILTER GATE     │                                │
    │   drop spam / noise   │                                │
    └──────────┬────────────┘                                │
               │                                             │
               ▼                                             │
    ┌───────────────────────┐                                │
    │   MESSAGE PARSER      │                                │
    │   Haiku LLM           │                                │
    │   multilingual extract│                                │
    └──────────┬────────────┘                                │
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │ both paths join at Step 3
                                      │
                          Leads arrive as a batch
                                      │
                    ┌─────────────────┴──────────────────┐
                  Lead 1           Lead 2            Lead N
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │ LEAD ENRICHMENT│  │LEAD ENRICHMT│  │LEAD ENRICHMT  │
          │  Consent Gate  │  │ Consent Gate│  │ Consent Gate  │
          │  collect data  │  │ collect data│  │ collect data  │
          │  extract sigs  │  │ extract sigs│  │ extract sigs  │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │   NORMALISE    │  │  NORMALISE  │  │  NORMALISE    │
          │ clean + unify  │  │ clean+unify │  │ clean + unify │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │  INTENT GATE   │  │ INTENT GATE │  │ INTENT GATE   │
          │pass↓  pause↗   │  │pass↓ pause↗ │  │pass↓  pause↗  │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
              ↗ await_clarification: lead paused, clarification sent via
                originating channel; resumes on reply OR scores with
                intent penalty after 24h — see Section 8.1
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │ SCORING AGENT  │  │SCORING AGENT│  │ SCORING AGENT │
          │  Sonnet        │  │  Sonnet     │  │  Sonnet       │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
                    │                │                   │
                    └────────────────┴───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │            BUCKETIZE                │
                    │   HOT  /  WARM  /  COLD             │
                    │   disqualification gate             │
                    │   completeness routing              │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │  DELIVERY AND INTEGRATION LAYER      │
                    │  chat cards · notifications · CRM    │
                    │  dashboards · reports · webhooks     │
                    │  [[analyses/delivery-integration-    │
                    │    layer]]                           │
                    └─────────────────────────────────────┘
```

Each lead is processed in parallel (up to a concurrency cap of `[TBD — recommend 5]` simultaneous Scoring Agent calls). DM-path leads also have a Message Parser (Haiku) call earlier in the flow; Lead Ad events skip Steps 0–2 and enter at the Lead Enrichment stage.

### 4.3 Stage Details

---

**Stage 1 — Data Gather**

Fetches all new leads from every channel the tenant has connected. All channels are called at the same time. After fetching, leads are deduplicated (phone first → email second → name + location as fallback).

**If one channel fails:** log it, notify the admin, continue with the rest. One broken channel never stops the others.

**If all channels fail:** halt the entire run and tell the user which channels failed and why.

---

**Stage 2 — Lead Enrichment**

Two things happen here, in sequence:

**(a) Consent Gate (runs before external enrichment)**

Before any external data lookup, the orchestrator checks jurisdiction-specific consent requirements: DPDP (India) and GDPR (EU/UK). Leads where consent cannot be confirmed are not sent to external enrichment providers — they are scored on internal signals only and flagged accordingly. Full rules: [[analyses/global-data-collection-architecture]] Section 10 (Consent Gate).

**(b) Collect more data about the lead**

The orchestrator gathers additional information from available sources — website visit history, social profiles, company data, internal CRM records, chat transcripts, past orders, external news. Internal history is always checked first before any external lookup.

**(c) Extract signal values (deterministic — no LLM)**

For each signal defined in Pipeline 2, the orchestrator runs the `detection_rule` against the collected data and extracts a value:

```
Pipeline 2 produced these signal slots:      Enrichment extracts these values:

  {pricing_request}          →    pricing_request   : true
  {demo_requested}           →    demo_requested    : false
  {urgency_language}         →    urgency_language  : true
  {response_speed}           →    response_speed    : "fast"
  {revisit_count}            →    revisit_count     : 3
  ...                             ...
```

This is fully deterministic. No LLM is involved. The extracted values go directly into the prompt template slots before the Scoring Agent is called.

**Why not use an LLM to extract signals?** Two reasons. First, debuggability: if a score is wrong, deterministic extraction lets you isolate whether the signal value was extracted incorrectly (enrichment bug) or evaluated incorrectly (scoring bug) — mixing the two makes both harder to diagnose. Second, cost: signal extraction runs for every signal on every lead; keeping this deterministic avoids adding an LLM call at the highest-frequency step in the pipeline. Note: the Message Parser (Haiku, DM path only) handles raw message text before signal extraction — it is a separate and cheaper step, not the same as LLM-based signal evaluation.

---

**Stage 3 — Normalise**

Standardises everything into a clean, consistent format before it goes to the Scoring Agent:

- Phone → E.164 format (`+91XXXXXXXXXX`)
- Name → Title Case, no emojis
- Location → city, state, country, tier (1 / 2 / 3)
- Dates → ISO 8601 UTC
- Product interest → mapped to internal taxonomy `[TBD per tenant]`

Also assigns a **data completeness score** to the lead:

| Level | Completeness | Meaning |
|---|---|---|
| Complete | 80–100% | All key fields present and verified |
| Partial | 50–79% | Some gaps, mostly verifiable |
| Sparse | < 50% | Significant missing data — the Scoring Agent uses this when calculating confidence |

**Conflict resolution:** most recent data wins for contact details. CRM data overrides self-reported data. If a conflict can't be resolved → store both values, flag for human review, log the conflict.

---

**Stage 4 — Scoring Agent (LLM)**

This is the primary LLM call in Pipeline 1 and runs for every lead on both the DM path and the Lead Ad path. On the DM path only, a second LLM call (Message Parser, Haiku model) fires earlier in the pipeline to extract structured fields from raw multilingual message text — see [[analyses/global-data-collection-architecture]] Section 5. The Scoring Agent always uses the Sonnet model regardless of path. The orchestrator prepares the filled prompt and calls the Scoring Agent:

```
Orchestrator prepares the call:

1. Load prompt template from prompt_registry (this tenant, this use case)
2. Fill every signal slot with the value extracted in Stage 2
3. Inject the completeness score from Stage 3
4. Record the prompt_version in the lineage log
5. Call Scoring Agent
```

**The filled prompt looks like this:**

```
[Scoring instructions]
[Gamoft persona and ICP injected]

Score this lead across 5 dimensions:

FIT SIGNALS:
  - industry_match   : true
  - role_relevance   : true
  - serviceability   : true

INTENT SIGNALS:
  - pricing_request  : true
  - demo_requested   : false
  - urgency_language : true

ENGAGEMENT SIGNALS:
  - response_speed   : fast
  - revisit_count    : 3

[Return JSON: bucket, total_score, dimension_scores, explanation_reasons, suggested_action, confidence]
```

**What the Scoring Agent returns — now locked by S2:**

S2's intelligence layer design has defined the full output schema. Here it is, with field-by-field explanation:

```json
{
  "score": 84,
  "bucket": "hot",
  "reasoning": "Strong ICP fit and explicit high-intent signals (pricing, timeline, scope) from a multi-channel active lead — recommend immediate outreach.",
  "lead_completeness": 0.87,
  "sub_scores": {
    "fit": 21,
    "intent": 25,
    "engagement": 17,
    "behaviour": 12,
    "context": 9
  },
  "recommended_action": "Call today — high intent, strong fit",
  "needs_review": false,
  "schema_version": "v1.0",
  "prompt_version": "v1.3.0",
  "model": "claude-sonnet-4-6"
}
```

**What each field means:**

| Field | Type | Description |
|---|---|---|
| `score` | int (0–100) | The overall lead score |
| `bucket` | string (lowercase) | `hot`, `warm`, or `cold` — the Output Schema Layer also validates this against the banding rule |
| `reasoning` | string | One-line explanation of why the lead got this score |
| `lead_completeness` | float (0.0–1.0) | How complete the enriched lead data was. **This is not LLM confidence.** It measures whether the Scoring Agent had enough data to work with — not how certain it is about its own reasoning. A score of 0.87 means 87% of expected signal fields were present and populated |
| `sub_scores` | object | Per-dimension breakdown. Always included — never collapsed into a single number |
| `recommended_action` | string | Specific suggested next step for the salesperson |
| `needs_review` | bool | Set to `true` by the Output Schema Layer when `lead_completeness` is below the configured threshold. When `true`: score is still stored and the lead is still delivered — but it is also routed to the human review queue |
| `schema_version` | string | Which version of the output schema this response conforms to |
| `prompt_version` | string | Which prompt template was used. Enables attribution in the feedback loop |
| `model` | string | Which model produced this output |

**sub_scores — resolved 2026-05-03:** Five fields, one per scoring dimension: `fit`, `intent`, `engagement`, `behaviour`, `context`. The earlier four-field schema that listed `recency` as a fourth field was a provisional placeholder — `recency` does not correspond to any of the five defined dimensions and is removed. All five dimension keys must always be present in the returned object. A value of zero means no signal in that dimension fired; it is never omitted.

Dimension scores are always shown separately — they are never collapsed into one number. A lead that is high on intent but low on fit needs completely different action than the reverse.

**Scoring Agent failure handling:**

| What goes wrong | What the orchestrator does |
|---|---|
| Malformed JSON returned | Retry once — append schema reminder to the prompt |
| Output doesn't match expected schema | Retry once |
| Timeout | Retry once with extended deadline |
| Rate limit hit | Wait for the rate limit window, retry once |
| Two consecutive failures | Stop trying — route lead to human review queue (`reason: scoring_failed`) |

---

**Stage 5 — Bucketize**

Deterministic. The orchestrator reads `total_score` and assigns a bucket:

| Bucket | Score range | Contact SLA |
|---|---|---|
| HOT | 80–100 | Salesperson must contact within 24 hours |
| WARM | 55–79 | Contact within 2–3 days |
| COLD | 0–54 | Weekly nurture or archive |

Thresholds are tenant-configurable starting points. They will be calibrated after Month 1 data using the AP1 and AP2 quality metrics.

**Disqualification gate (runs before bucketing):**

Some conditions override the score entirely, regardless of what the Scoring Agent returned:

| Condition | What happens |
|---|---|
| Outside serviceable area | Score capped at 50, or marked disqualified |
| Wrong geography | −30 points |
| Non-decision-maker | −40 points |
| Student / spam / clearly irrelevant | Score forced to 0 |

Exact disqualification rules: `[TBD per tenant]`

**Lead completeness routing (runs after bucketing):**

The `needs_review` flag in the ScoringOutput (set by S2's Output Schema Layer) is what drives routing here. The Output Schema Layer reads `lead_completeness` and sets `needs_review = true` if it falls below a configured threshold. The orchestrator reads `needs_review` and acts on it.

| Lead completeness | What happens | Why this threshold |
|---|---|---|
| ≥ 80% | Auto-assign bucket, write to output — no human needed | High completeness means the Scoring Agent had enough signal data and strong dimension coverage — human review adds no value |
| 50–79% | Assign bucket but add a WARNING flag — salesperson can review | Moderate completeness means at least one dimension had weak or missing signals — the bucket is likely correct but worth a second look |
| < 50% | `needs_review = true` — route to human review queue | Low completeness means the system was scoring from thin data and cannot reliably distinguish between buckets for this lead |

**What "human review queue" actually is:** There is no separate `human_review_queue` table. Human review is just a filtered view of the `leads` table where `pipeline_stage = 'human_review'`. S1 confirms the `lead` entity covers this — no additional table needed.

**How these bands connect to quality metrics:** The split of leads across the three completeness bands is captured as the per-run lead completeness distribution metric (computed at the end of every Pipeline 1 run and written to `quality_snapshots`). A run where more than 50% of leads fall below 50% completeness triggers an alert — it signals that enrichment is failing to collect enough data on too many leads. See [[analyses/governance-observability-layer]] Section 2.3 and [[analyses/scoring-quality-metrics]] for the full metric definitions.

---

## 5. Governance Layer

The Governance Layer is not part of either pipeline's sequential flow. It runs alongside both pipelines, receives events from them continuously, and runs its own scheduled jobs independently.

**Rule: a failure in the Governance Layer must never halt Pipeline 1 or Pipeline 2.**

| Domain | What it does |
|---|---|
| Monitoring | Tracks per-run metrics, confidence distributions, failure rates, SLA breaches |
| Auditability | `pipeline_log` (every transformation) + `access_log` (every user action) |
| Lineage | Full provenance per lead, per stage — written by orchestrator at every step |
| Feedback loops | Attribution → pattern detection → team lead recommendation → human-approved action |
| Quality tracking | Scheduled SQL jobs at 3 cadences (per-run, weekly, monthly) → `quality_snapshots` table — metrics defined in [[analyses/scoring-quality-metrics]] |
| Security | Postgres RLS + JWT with tenant_id claim + 4-role RBAC + secrets vault + PII encryption at rest |

Run-level data from both pipelines feeds the three Global KPIs defined in [[analyses/scoring-quality-metrics]]: **System Health** (Pipeline Coverage + Score Stability, reviewed weekly by the engineering lead), **Business Health** (Scoring Lift + HOT Response Rate, reviewed monthly by the product owner), and **Tenant Health Rate** (reviewed monthly once Month 1 baseline thresholds are set). A drop in System Health is an engineering escalation — it means the orchestrator is losing leads before scoring or producing inconsistent scores across runs.

Full documentation: [[analyses/governance-observability-layer]]

### 5.1 Quality Metrics Orchestration Flow

This diagram shows the full lifecycle: how raw pipeline events become quality metrics, how metrics become Global KPIs, and how KPI review feeds back into orchestrator configuration.

```
  PIPELINE 1 RUN ENDS         PIPELINE 2 ONBOARDING ENDS
         │                               │
         │  orchestrator writes          │  orchestrator writes
         │  per-lead lineage             │  onboarding lineage
         └───────────────┬───────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────────┐
        │               pipeline_log               │
        │  confidence · dimension_scores           │
        │  prompt_version · signal_version         │
        │  fired_signals · pipeline_stage          │
        │  run_id · lead_id · tenant_id            │
        └────────┬────────────────────────────────-┘
                 │         also reads: leads table
                 │         also reads: feedback_events table
                 │
     ┌───────────┴────────────────────────────────┐
     │                                            │
     ▼  (immediate — fires at end of every run)   ▼  (Monday 00:00 — scheduled)
┌─────────────────────┐                  ┌──────────────────────────┐
│     PER-RUN SQL     │                  │      WEEKLY SQL JOB      │
│                     │                  │                          │
│  Score Coverage     │                  │  AR1  SLA Compliance     │
│  Confidence bands   │                  │  AR2  Action Rate        │
│  Bucket dist.       │                  │  AR3  Time-to-Action     │
│  Pipeline failures  │                  │  AR4  Action Types       │
│  Human review rate  │                  │  C1   Bucket Stability   │
└──────────┬──────────┘                  │  C2   Score Drift        │
           │                             └──────────────┬───────────┘
           │                                            │
           │             ┌──────────────────────────────┘
           │             │
           │             │        ┌────────────────────────────────────┐
           │             │        │         MONTHLY SQL JOB            │
           │             │        │  (minimum 100 outcomes per bucket) │
           │             │        │                                    │
           │             │        │  AP1  Bucket Outcome Rate          │
           │             │        │  AP2  Discrimination Ratio         │
           │             │        │  AP3  Completeness Qualifier       │
           │             │        │  C4   Decay-Rescore Coherence      │
           │             │        │  AR5  Priority Alignment           │
           │             │        └──────────────────┬─────────────────┘
           │             │                           │
           └─────────────┴───────────────────────────┘
                                     │
                                     ▼
                       ┌─────────────────────────┐
                       │     quality_snapshots    │
                       │  (one row per metric,    │
                       │   per tenant, per run)   │
                       └────────────┬────────────-┘
                                    │
               ┌────────────────────┼─────────────────────┐
               ▼                    ▼                      ▼
  ┌────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
  │   System Health    │  │   Business Health    │  │  Tenant Health Rate  │
  │                    │  │                      │  │                      │
  │  Pipeline Coverage │  │  Scoring Lift        │  │  % tenants where all │
  │  (Score Coverage   │  │  (AP2 Discrimination │  │  primary metrics are │
  │   Rate avg across  │  │   Ratio, median      │  │  within range        │
  │   all tenants)     │  │   across tenants)    │  │                      │
  │                    │  │                      │  │  NOT live until      │
  │  Score Stability   │  │  HOT Response Rate   │  │  Month 1 baseline    │
  │  (C1 Bucket        │  │  (AR1 HOT SLA        │  │  thresholds are set  │
  │   Stability avg    │  │   Compliance avg     │  │                      │
  │   across tenants)  │  │   across tenants)    │  │                      │
  │                    │  │                      │  │                      │
  │  WHO: Eng lead     │  │  WHO: Product owner  │  │  WHO: Product owner  │
  │  WHEN: weekly      │  │       + AI/ML owner  │  │  WHEN: monthly       │
  │  DROP = escalate   │  │  WHEN: monthly       │  │  (post-Month 1)      │
  └─────────┬──────────┘  └──────────┬───────────┘  └──────────┬───────────┘
            └─────────────────────────┼──────────────────────────┘
                                      │
                          team lead + product owner review
                                      │
               ┌──────────────────────┴────────────────────────┐
               │                                               │
               ▼                                               ▼
  ┌───────────────────────────┐              ┌────────────────────────────────┐
  │  Bucket Threshold         │              │  Feedback-Driven Action        │
  │  Recalibration            │              │                                │
  │                           │              │  Weight update                 │
  │  AP1 HOT outcome rate     │              │  → edit signal_definitions     │
  │  too low → lower HOT      │              │    .weight_within_dimension    │
  │  boundary (e.g. 80→75)    │              │                                │
  │                           │              │  Prompt update                 │
  │  AP2 ratio near 1 →       │              │  → new version in              │
  │  buckets not separating   │              │    prompt_registry             │
  │  → review signal weights  │              │                                │
  │                           │              │  ICP + Signal Agent re-run     │
  │  [Month 1 minimum         │              │  → triggers Pipeline 2         │
  │   before first adjustment]│              │  → team lead must approve      │
  └─────────────┬─────────────┘              └──────────────┬─────────────────┘
                └──────────────────────┬────────────────────┘
                                       │ human-approved only [LOCKED]
                                       ▼
              ┌────────────────────────────────────────────────┐
              │                  ORCHESTRATOR                   │
              │                                                │
              │  Updated bucket thresholds in tenant_config    │
              │  Updated signal weights in signal_definitions  │
              │  New prompt_version active in prompt_registry  │
              │  New signal_version (if Pipeline 2 re-ran)     │
              │                                                │
              │  → Applied on the next Pipeline 1 run          │
              └────────────────────────────────────────────────┘
```

**How to read this diagram:**

| Layer | What it produces | Who consumes it |
|---|---|---|
| pipeline_log | Raw event data per lead per stage | SQL jobs (all three cadences) |
| Per-run SQL | Operational health signal — is the pipeline working right now? | Engineering lead (immediate alert if threshold breached) |
| Weekly SQL | Behaviour signal — are salespeople acting on scores? | Team lead reviews Monday |
| Monthly SQL | Business value signal — is scoring separating good leads from bad? | Team lead + product owner monthly |
| quality_snapshots | Stored metric values per tenant per cadence | Global KPI computation |
| Global KPIs | Executive-level one-view summary | Product owner, reviewed monthly |
| Recalibration | Config changes that close the improvement loop | Orchestrator on next run |

**The loop is intentionally slow.** Per-run fires immediately, but bucket recalibration only happens after monthly data accumulates — because outcome data (whether a HOT lead actually converted) takes weeks to resolve. Rushing the feedback loop before enough data exists would produce changes based on noise, not signal.

---

## 6. Orchestration Controller — What It Does

### 6.1 Running Pipeline 2

```
1. Collect tenant business information from onboarding flow
2. Call Onboarding Agent → receive persona object → store in `personas` table
3. Call ICP Agent (input: persona) → receive ICP → store
4. Call Signal Agent (input: persona + ICP) → receive signal definitions → store in `signal_definitions`
5. Generate prompt template using signal names as slot labels → store in `prompt_registry`
6. Write lineage entries to pipeline_log for each agent call
7. Set tenant.status = 'active'
```

### 6.2 Pre-Flight Check Before Every Pipeline 1 Run

Before any lead is processed, the orchestrator checks:

```
Is tenant.status = 'active'?
Do signal_definitions exist for this tenant?
Does a prompt_template exist for this tenant and use case?

→ If anything is missing: HALT. Tell the user to complete onboarding first.
→ If all present: proceed.
```

### 6.3 Running Pipeline 1

```
1.  Classify user intent (if interactive) or read trigger params (if scheduled/webhook)
2.  Load tenant_config + persona + signal_definitions + prompt_template from DB
3.  Generate a unique run_id
4.  Resolve capability registry → get the tool sequence for this use case
5.  Call Data Gather → fetch all leads across all channels in parallel
6.  Fan out per lead (parallel, up to concurrency cap):
      a. Lead Enrichment — collect data + extract signal values
      b. Normalise — clean and standardise
      c. Fill prompt template with extracted signal values
      d. Call Scoring Agent
      e. Validate output against expected schema
7.  Wait for all leads to reach a terminal state
8.  For each lead: run disqualification gate → apply confidence routing → assign bucket → assign SLA
9.  Write run-level observability log
10. Hand off to Delivery and Integration Layer — ranked lead cards delivered in chat (HOT leads pushed immediately), HOT/WARM leads pushed to CRM, notifications dispatched. See [[analyses/delivery-integration-layer]].
```

---

## 7. Tool Invocation — How the Orchestrator Calls Tools

### 7.1 Capability Registry

The capability registry tells the orchestrator which tools to call, in what order, for each use case. It is loaded once at the start of each Pipeline 1 run.

```
use_case: lead_enrichment
tools:    [data_gather, lead_enrichment, normalise, scoring_agent, bucketize]
```

**Adding a new use case = one new registry entry. Zero orchestrator code changes.**

Storage format: `[TBD — YAML / JSON / DB table]`

### 7.2 Standard Call Format

Every tool call from the orchestrator uses the same input and output shape. This is currently a proposal — needs confirmation from S1 and S2.

**Input (per-lead tools: enrichment, normalise, scoring agent, bucketize):**

```json
{
  "run_id": "uuid",
  "lead_id": "uuid",
  "tenant_id": "string",
  "stage": "enriched | normalised | scored",
  "input_data": { },
  "context": {
    "persona": { },
    "tenant_config": { },
    "signal_definitions": [ ],
    "prompt_template_version": "string"
  }
}
```

**Output (all tools):**

```json
{
  "status": "success | failure",
  "output_data": { },
  "error": "string or null",
  "duration_ms": 123,
  "prompt_version": "string or null"
}
```

**Input (run-level tools: data_gather):**

```json
{
  "run_id": "uuid",
  "tenant_id": "string",
  "source_list": ["whatsapp", "facebook", "instagram", "website"],
  "config": { "quotas": { }, "credentials_ref": "vault_path" }
}
```

**Input (Pipeline 2 agents: onboarding, icp, signal):**

```json
{
  "tenant_id": "string",
  "pipeline": "onboarding",
  "stage": "persona | icp | signals",
  "input_data": { },
  "prompt_version": "string"
}
```

### 7.3 Retry Rules

| Tool type | On failure |
|---|---|
| Deterministic tools (enrichment, normalise, bucketize) | 1 retry → if still fails → mark lead `failed`, continue the rest of the run |
| Pipeline 2 LLM agents (Onboarding, ICP, Signal) | 1 retry → if still fails → halt onboarding entirely, alert the admin |
| Pipeline 1 Scoring Agent | See the Scoring Agent failure table in Section 4.3 Stage 4 |

**Note on enrichment retries — added 2026-05-03:** The "1 retry" rule above is the orchestrator-level retry (calls the enrichment tool a second time if it returns a failure status). It is separate from, and does not replace, the API fallback chain that operates *inside* the Lead Enrichment tool: when a specific provider (e.g. Apollo.io) returns no result, the enrichment tool automatically tries the next provider in the Source Registry fallback chain before returning a failure to the orchestrator. The 1-retry rule only fires if the enrichment tool itself returns failure after exhausting its internal fallback chain. See [[analyses/lead-enrichment-architecture]] for the full fallback chain and [[analyses/global-data-collection-architecture]] Section 7 for the Source Registry model.

---

## 8. State Tracking — How the Orchestrator Knows Where Everything Is

### 8.1 Lead Stage Transitions

Every lead has a `pipeline_stage` field. The orchestrator reads and writes this field at every step.

```
captured
  → fetched          after Data Gather completes
    → enriched       after Lead Enrichment completes
      → normalised   after Normalise completes
        → scored     after Scoring Agent returns valid output

From scored, one of four outcomes:
  → delivered                bucket assigned, SLA set, written to salesperson output
  → human_review             lead_completeness < 50% OR scoring failed after retries
  → awaiting_clarification   very_low intent signal + high fit score; orchestrator sends
                             a clarification prompt to the lead via the originating channel;
                             pipeline is paused; resumes at normalised stage on reply;
                             if no reply within 24 hours → scores with an intent penalty
                             and transitions to delivered. See [[analyses/global-data-collection-architecture]]
                             Section 9 (Intent Gate).

From any non-terminal stage:
  → failed           retries exhausted
```

**Terminal states:** `delivered`, `human_review`, `failed`

**Non-terminal holding state:** `awaiting_clarification` — the lead is paused and waiting for input from the prospect. It must be treated as non-terminal by the concurrency guard: a lead in `awaiting_clarification` is not stale and must NOT be resumed by the crash-recovery path. The orchestrator distinguishes it from a crashed-run hold by checking whether the stage is exactly `awaiting_clarification` before applying the timeout logic in Section 8.3.

These pipeline_stage values are now locked. S1's entity catalog confirms the `lead` entity exists and carries this field. The accepted string values above are the ones S1 must implement — they are not flexible. Every orchestrator read and write depends on exactly these strings. If S1 ever changes a value (e.g. `normalised` → `normalized`), the orchestrator breaks silently at runtime.

### 8.2 The Write Order Rule

After every tool call, the orchestrator writes in this exact sequence:

```
Step 1 → Tool returns its output
Step 2 → Orchestrator writes lineage entry to pipeline_log
Step 3 → Orchestrator writes output_data to the leads table
Step 4 → Orchestrator updates pipeline_stage          ← always last
```

`pipeline_stage` is always the final write. If the system crashes anywhere between Step 1 and Step 4, the stage stays at its previous value. On restart, the orchestrator sees that stage and retries from there. **This is the crash safety guarantee.**

### 8.3 Concurrency Guard

When a run starts and a lead's `pipeline_stage` is non-terminal, the orchestrator needs to know whether that lead is currently being processed by another run or was abandoned by a crashed run. It decides by checking how recently the lead was updated:

```
If pipeline_stage is terminal (delivered / human_review / failed):
  → Skip. Already done.

If pipeline_stage is awaiting_clarification:
  → Skip. The lead is intentionally paused waiting for prospect reply.
    The 24-hour timeout is handled by a dedicated scheduled job, not here.

If pipeline_stage is non-terminal (not terminal, not awaiting_clarification)
  AND last_updated is older than [TBD: 15–30 min]:
  → Resume. The previous run must have crashed.

If pipeline_stage is non-terminal (not terminal, not awaiting_clarification)
  AND last_updated is recent:
  → Skip. Another run is actively processing this lead right now.
```

Different leads never share mutable state, so leads processed in parallel never interfere with each other. Different tenants are fully isolated by `tenant_id`.

### 8.4 Crash Recovery

If the orchestrator crashes mid-run and restarts:

```
1. Query: all leads WHERE pipeline_stage is non-terminal
                      AND pipeline_stage != 'awaiting_clarification'
                      AND last_updated older than timeout_threshold
2. Reconstruct run context from pipeline_log using run_id
3. For each recoverable lead: re-enter Pipeline 1 at its current stage
4. Max 2 total retries per stage per lead
   → after 2 failures: mark the lead failed, move on
```

`awaiting_clarification` leads are intentionally excluded from crash recovery — their timeout is handled by a separate scheduled job, not here.

**One accepted tradeoff:** if the Scoring Agent was mid-call when the crash happened, it will be called again on recovery. This means one extra LLM cost for that lead. This is accepted — the `prompt_version` field in the lineage log means any scoring drift is visible and traceable.

**Idempotency requirement for S1 and S2:** every tool must be idempotent at its stage boundary. Calling the same tool twice with the same input must produce equivalent output and must not corrupt state.

### 8.5 Lineage Writes

The orchestrator writes a `pipeline_log` entry after **every tool call, at every stage, in both pipelines**. Individual tools never write lineage — only the orchestrator does.

**Update from S1 (2026-04-22):** What this document previously called `pipeline_log` (one table) is actually three separate entities in S1's data model. Here is how they map:

| Old name | S1 entity | What it records |
|---|---|---|
| pipeline_log (run header) | `pipeline_run` | One record per complete workflow execution — did the whole run succeed? Start time, end time, pipeline type, status |
| pipeline_log (stage rows) | `task_execution` | One record per stage per run — which stage, which status, how long, retries, errors |
| pipeline_log (provenance) | `lineage_record` | The data provenance chain — what went in, what came out, how data moved through enrichment/scoring/aggregation |

**Why three tables, not one:** Each answers a different question. `pipeline_run` tells you whether the business process succeeded. `task_execution` tells you exactly which stage failed and why. `lineage_record` tells you how a specific output was produced from a specific input. Mixing them into one table makes all three questions harder to answer cleanly.

**For the orchestrator, the write sequence per stage is:**

```
1. Tool returns its output
2. Orchestrator writes to lineage_record (provenance of this stage's transformation)
3. Orchestrator writes to task_execution (step-level status for this stage)
4. Orchestrator updates pipeline_run (run-level status if this was the last stage)
5. Orchestrator updates leads.pipeline_stage     ← always last
```

**Fields the orchestrator writes to each:**

`task_execution` (per stage):

| Field | What it captures |
|---|---|
| `run_id` | Which pipeline run this stage belongs to |
| `lead_id` | Which lead (null for Pipeline 2 stages) |
| `agent_id` | Which tool or agent executed this stage |
| `tenant_id` | Which tenant |
| `pipeline` | `onboarding` or `lead_processing` |
| `timestamp` | When the stage started |
| `duration_ms` | How long the stage took |
| `status` | success / failure |
| `retry_count` | How many times this stage was retried |
| `error` | Error message on failure, null on success |

`lineage_record` (per stage, data provenance):

| Field | What it captures |
|---|---|
| `run_id` | Which run |
| `lead_id` | Which lead |
| `agent_id` | Which tool produced this entry |
| `tenant_id` | Which tenant |
| `input_snapshot` | Exact input sent to the tool |
| `output_snapshot` | Exact output the tool returned |
| `prompt_version` | Active prompt version — null for non-LLM tools |
| `lead_completeness` | Lead completeness score — null before the scoring stage |

Note: `lead_completeness` replaces what was previously called `confidence` in this field. See [[concepts/confidence-first-class]] for the full correction.

Concurrent writes across parallel leads are safe — each `task_execution` entry is unique on `(run_id, lead_id, stage)`.

**The lineage log is the primary data source for all scoring quality metrics.** The fields written here — especially `confidence`, `dimension_scores`, `prompt_version`, `signal_version`, and `fired_signals` — are exactly what the quality metric jobs in [[analyses/scoring-quality-metrics]] compute against. The orchestrator writing complete, accurate lineage after every stage is the prerequisite for every metric in that document. A missing lineage entry means a missing data point in the quality snapshot; a corrupt entry means a corrupt metric. The lineage write is not optional bookkeeping — it is the foundation of the measurement system.

| Lineage field | Where it lives | Quality metrics that depend on it |
|---|---|---|
| `lead_completeness` | `lineage_record` | Per-run completeness distribution; C1, C2 (cross-run stability checks filter by completeness) |
| `sub_scores` | `lineage_record` output_snapshot | AP1, AP2 (bucket outcome rates need per-dimension breakdown) |
| `prompt_version` | `lineage_record` | Attribution job (Step 1 of feedback loop) — identifies which prompt version appears in wrong-bucket patterns |
| `fired_signals` | `lineage_record` output_snapshot | AP3 (completeness qualifier), C5 (signal contribution consistency spot-check) |
| `pipeline_stage` | `leads` table | Score Coverage Rate — denominator is leads that entered; numerator is leads that reached `scored` stage |
| `status` + `retry_count` | `task_execution` | Pipeline failure rate, per-stage bottleneck identification |

**Build lineage before adding the second LLM agent.** Retrofitting an audit trail across multiple running agents is extremely costly and error-prone.

---

## 9. What S1 and S2 Need to Deliver

The orchestrator sits between the data layer (S1) and the intelligence layer (S2). It cannot be fully built without interface contracts from both.

**Status updated 2026-04-22** — S1 has delivered the entity catalog and S2 has delivered the intelligence layer design. Most blockers are resolved.

### Hard Blockers — orchestrator code cannot be written without these

| What is needed | Who delivers | Status |
|---|---|---|
| `leads.pipeline_stage` — exact field name and all accepted string values | S1 | **RESOLVED** — values locked by this document: captured → fetched → enriched → normalised → scored → delivered / human_review / awaiting_clarification / failed. `awaiting_clarification` added 2026-05-03 (Intent Gate, DM path). S1 implements exactly these strings. |
| Data store for pipeline execution and lineage | S1 | **RESOLVED** — three entities confirmed: `pipeline_run` (run-level), `task_execution` (step-level), `lineage_record` (provenance). Orchestrator writes to all three after every stage. |
| Scoring Agent output JSON schema | S2 | **RESOLVED** — schema locked. Key fields: `score` (int), `bucket` (lowercase string), `reasoning` (string), `lead_completeness` (float 0.0–1.0), `sub_scores` (object), `recommended_action` (string), `needs_review` (bool), `schema_version`, `prompt_version`, `model`. |
| Signal `detection_rule` format and evaluation engine | S2 | **RESOLVED 2026-04-28** — named extractor + params. See [[analyses/signal-detection-rule-spec]]. |

### Soft Blockers — resolved

| What is needed | Who delivers | Status |
|---|---|---|
| `tenant_config` mandatory field list | S1 | **RESOLVED** — mandatory fields are tenant_id, business_type, and the business_profile fields that feed the PersonaObject (icp, scoring_weights, banding, custom_rules, tone). |
| `signal` entity schema | S1 | **RESOLVED** — confirmed: signal_id, dimension, name, description, detection_rule, weight_within_dim, applicable_to. `signal_evaluation` is the companion entity storing per-lead answers. |
| `human_review_queue` — is it a separate table? | S1 | **RESOLVED — no separate table.** Human review leads are a filtered view of the `leads` table where `pipeline_stage = 'human_review'`. The `needs_review` flag in the ScoringOutput is what routes a lead there. |
| Persona object (Onboarding Agent output) | S2 | **RESOLVED** — PersonaObject fields: tenant_id, business_type (B2B/B2C), icp (IcpDefinition), scoring_weights {fit, intent, engagement, behaviour, context}, banding {hot_min, warm_min, cold_max}, custom_rules (list), tone, version. Cached by Persona Engine with 15-min TTL. |
| ICP object (ICP Agent output) | S2 | **RESOLVED** — ICP output is captured as `icp: IcpDefinition` inside the PersonaObject, and stored separately as the `ideal_customer_profile` entity by S1. Also versioned in `ideal_customer_profile_version`. |
| Signal Agent output schema | S1 + S2 | **RESOLVED** — Signal Agent outputs `signal` records (one per scoring question). Stored by S1 in the `signal` entity. |

---

## 10. Open Decisions

Updated 2026-04-22 — items resolved by S1 entity catalog and S2 intelligence layer design are marked.

| Decision | Owner | Status |
|---|---|---|
| `leads.pipeline_stage` exact accepted values | S1 | **RESOLVED** — locked by this document |
| Data store for lineage and execution tracking | S1 | **RESOLVED** — three entities: pipeline_run, task_execution, lineage_record |
| `signal` and `signal_evaluation` entity schemas | S1 | **RESOLVED** — confirmed in S1 entity catalog |
| `human_review_queue` existence and schema | S1 | **RESOLVED** — no separate table; filtered view of leads |
| Scoring Agent output schema (incl. completeness field) | S2 | **RESOLVED** — locked by S2 design spec |
| Onboarding / ICP / Signal Agent output schemas | S2 | **RESOLVED** — PersonaObject, IcpDefinition, and signal entity all defined |
| Signal `detection_rule` format + evaluation engine | S2 | **RESOLVED 2026-04-28** — see [[analyses/signal-detection-rule-spec]]. |
| Sub_scores field list | S2 | **RESOLVED 2026-05-03** — five fields matching the five dimensions: `fit`, `intent`, `engagement`, `behaviour`, `context`. The former `recency` field was a provisional placeholder with no corresponding dimension and is removed. |
| Scoring Agent concurrency cap | Team | Recommend 5; team decision needed |
| Timeout threshold for concurrency guard | Team | Recommend 15–30 min; team decision needed |
| Capability registry storage format | Team | YAML / JSON / DB table — team decision |
| Tool invocation envelope — confirm the proposed shape | S1 + S2 | Still needs review from both sides |
| Disqualification rules per tenant | Per tenant | Defined at tenant onboarding |
| Bucket threshold calibration (after Month 1 data) | Team | Starting points locked (80/55/0); recalibrate after Month 1 using AP1/AP2 |
| Pipeline 2 check-in cadence | Team | Suggest 2 weeks or monthly |
| Alert delivery channel (chat / email / both) | Team | TBD |
| Lead completeness threshold for needs_review | Team | S2 suggests 0.6 or 0.75 as starting options; team decision |

---

## 11. Confirmed Decisions

| Decision | Basis |
|---|---|
| Orchestrator is deterministic — makes no LLM calls | Team decision |
| Two-pipeline architecture: Pipeline 2 (setup) + Pipeline 1 (per lead) | Team decision 2026-04-19 |
| 4 LLM agents total (3 in Pipeline 2, 1 in Pipeline 1) | Team decision 2026-04-19 |
| LLM calls per lead: one Sonnet call (Scoring Agent, all paths) + one Haiku call (Message Parser, DM path only) — revised 2026-05-03 | Team decision; global-data-collection-architecture 2026-05-03 |
| Signal extraction is deterministic — no LLM | Team decision 2026-04-19 |
| Scoring Agent uses fill-in-the-blanks prompt template | Team decision 2026-04-19 |
| Bucket thresholds: HOT ≥ 80, WARM ≥ 55, COLD < 55 (tenant-configurable starting points) | Playbook + team 2026-04-19 |
| Cross-lead parallel processing included from v2.0 | Confirmed 2026-04-19 |
| `pipeline_stage` is the final atomic write after every stage | Team decision |
| Lineage written by the orchestrator — not by individual tools | Team decision |
| Status-based concurrency guard (not DB locks) | Proposed to S1 |
| Crash recovery = resume from current `pipeline_stage` | Team decision |
| Score decay, SLA tracker, and feedback jobs run outside the orchestrator | Team decision |
| Governance layer failure must never halt Pipeline 1 or Pipeline 2 | Team decision |
| System proposes pipeline re-runs — team lead always approves | Locked principle |
| pipeline_stage accepted string values locked (see Section 8.1) — `awaiting_clarification` added 2026-05-03 | S1 entity catalog 2026-04-22; global-data-collection-architecture 2026-05-03 |
| Data store is three entities: pipeline_run, task_execution, lineage_record | S1 entity catalog 2026-04-22 |
| Scoring Agent output schema locked — `lead_completeness` (not `confidence`) | S2 intelligence layer design 2026-04-22 |
| sub_scores schema locked — five fields: fit, intent, engagement, behaviour, context; `recency` removed | global-data-collection-architecture 2026-05-03 |
| No separate human_review_queue table — filtered view of leads | S1 entity catalog 2026-04-22 |
| PersonaObject structure locked | S2 intelligence layer design 2026-04-22 |
| Signal + signal_evaluation are formal separate entities | S1 entity catalog 2026-04-22 |
| Three prompt variants: new, returning, rescore | S2 intelligence layer design 2026-04-22 |
| Intelligence layer never writes to data layer directly — all writes through orchestration | S2 intelligence layer design 2026-04-22 |
