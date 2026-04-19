---
type: analysis
question: "Document orchestration controller, tool invocation, and state tracking responsibilities."
date: 2026-04-19
tags: [orchestration, system-layer, subtask-3, spec, controller, state-tracking, tool-invocation, two-pipeline]
sources_consulted: [sources/2026-lead-intelligence-engine-reference, raw/assets/lead_intelligence_manual_enrichment_playbook]
related: [analyses/orchestration-layer-dependencies, analyses/governance-observability-layer]
status: COMPLETE
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
  │  Onboarding Agent (LLM) │         │   Data Gather                │
  │          ↓              │         │          ↓                   │
  │  ICP Agent (LLM)        │────────►│   Lead Enrichment            │
  │          ↓              │  signal │          ↓                   │
  │  Signal Agent (LLM)     │  defs + │   Normalise                  │
  │          ↓              │  prompt │          ↓                   │
  │  Prompt Template built  │         │   Scoring Agent (LLM)        │
  └─────────────────────────┘         │          ↓                   │
          │ lineage                   │   Bucketize → salesperson    │
          │ writes                    └──────────────┬───────────────┘
          │ (both pipelines)               lineage   │
          └────────────────────────────────writes ───┘
                                    │
              ┌─────────────────────▼────────────────────────────────┐
              │                GOVERNANCE LAYER                       │
              │   monitoring · auditability · feedback loops          │
              │   lineage (pipeline_log) · security                   │
              │                                                      │
              │   ┌─────────────────────────────────────────────┐   │
              │   │          QUALITY TRACKING                    │   │
              │   │   [[analyses/scoring-quality-metrics]]       │   │
              │   │                                              │   │
              │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
              │   │  │ PER-RUN  │  │  WEEKLY  │  │ MONTHLY  │  │   │
              │   │  │ Coverage │  │ AR1 SLA  │  │ AP1 BOR  │  │   │
              │   │  │ Confid.  │  │ AR2 Act  │  │ AP2 Sep  │  │   │
              │   │  │ Buckets  │  │ C1 Stab  │  │ AP3/C4   │  │   │
              │   │  │ Failures │  │ C2 Drift │  │ AR5 Algn │  │   │
              │   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  │   │
              │   │       └─────────────┼──────────────┘        │   │
              │   │                     ▼                        │   │
              │   │           quality_snapshots                  │   │
              │   │                     │                        │   │
              │   │        ┌────────────┼───────────┐            │   │
              │   │        ▼            ▼           ▼            │   │
              │   │    System       Business     Tenant          │   │
              │   │    Health       Health       Health          │   │
              │   │    (weekly)     (monthly)    Rate            │   │
              │   └─────────────────────────────────────────────┘   │
              │                        │                             │
              │           team lead + product owner review           │
              │           → recalibrate buckets (AP1 / AP2)         │
              │           → update weights / approve Pipeline 2      │
              └──────────────────────────────────────────────────────┘
                                        │ config applied to next run
                                        ▼
                                   ORCHESTRATOR
```

**There are 4 LLM agents in the entire system:**

| Agent | Pipeline | What it does |
|---|---|---|
| Onboarding Agent | Pipeline 2 | Converts tenant business info into a structured persona |
| ICP Agent | Pipeline 2 | Defines what the ideal customer looks like for this tenant |
| Signal Agent | Pipeline 2 | Creates the signal definitions used to evaluate every lead |
| Scoring Agent | Pipeline 1 | Scores each lead using the signal values extracted from enrichment |

**One LLM call per lead.** The three Pipeline 2 agents run once at onboarding. After that, only the Scoring Agent runs — once per lead.

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
  priority_signals      : what to weight most
  disqualifying_signals : what eliminates a lead immediately
  buying_triggers       : events that signal readiness to buy
  icp_examples          : example leads (real or synthetic)
}
```

Schema: `[TBD from S2]`

---

**Signal Agent → Signal Definitions**

Using both the persona and ICP, the Signal Agent creates the full list of signals across five dimensions:

| Dimension | Illustrative weight | What it captures |
|---|---|---|
| Fit | ~25% | Industry match, role match, serviceability, company size |
| Intent | ~30% | Price requests, demo requests, urgency language, timeline stated |
| Engagement | ~20% | Response speed, revisit count, multi-channel contact |
| Behavioral | ~15% | Past orders, prior proposals, payment patterns |
| Context | ~10% | Location, city tier, seasonality, external triggers |

Weights are per-tenant and configurable. These are illustrative starting points from the playbook.

Each signal is stored as:

```
{
  signal_id
  dimension            : fit | intent | engagement | behavioral | context
  name                 : "pricing_request"
  description          : "Lead explicitly asked for pricing or a quote"
  detection_rule       : how to extract this signal's value  [TBD from S2]
  weight_within_dim    : float
  applicable_to        : B2B | B2C | both
}
```

Stored in: `signal_definitions` table

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

For interactive triggers: the orchestrator classifies the intent before doing anything. If the intent is ambiguous, it presents 2–3 options to the salesperson and waits. It never guesses.

### 4.2 The Six Stages

```
                       TRIGGER (chat / schedule / webhook)
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │            DATA GATHER              │
                    │  Fetch all new leads from all       │
                    │  connected channels simultaneously  │
                    │  WhatsApp · Facebook · Instagram    │
                    │  Website forms · LinkedIn · etc.    │
                    └─────────────────┬───────────────────┘
                                      │
                          Leads arrive as a batch
                                      │
                    ┌─────────────────┴──────────────────┐
                  Lead 1           Lead 2            Lead N
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │ LEAD ENRICHMENT│  │LEAD ENRICHMT│  │LEAD ENRICHMT  │
          │  collect data  │  │ collect data│  │ collect data  │
          │  extract signal│  │ extract sig │  │ extract sig   │
          │  values        │  │ values      │  │ values        │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │   NORMALISE    │  │  NORMALISE  │  │  NORMALISE    │
          │ clean + unify  │  │ clean+unify │  │ clean + unify │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
                    │                │                   │
          ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼──────┐
          │ SCORING AGENT  │  │SCORING AGENT│  │ SCORING AGENT │
          │  (LLM call)    │  │ (LLM call)  │  │  (LLM call)   │
          └─────────┬──────┘  └──────┬──────┘  └────────┬──────┘
                    │                │                   │
                    └────────────────┴───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │            BUCKETIZE                │
                    │   HOT  /  WARM  /  COLD             │
                    │   disqualification gate             │
                    │   confidence routing                │
                    └─────────────────┬───────────────────┘
                                      │
                    Salesperson sees ranked lead cards in chat
```

Each lead is processed in parallel (up to a concurrency cap of `[TBD — recommend 5]` simultaneous Scoring Agent calls).

### 4.3 Stage Details

---

**Stage 1 — Data Gather**

Fetches all new leads from every channel the tenant has connected. All channels are called at the same time. After fetching, leads are deduplicated (phone first → email second → name + location as fallback).

**If one channel fails:** log it, notify the admin, continue with the rest. One broken channel never stops the others.

**If all channels fail:** halt the entire run and tell the user which channels failed and why.

---

**Stage 2 — Lead Enrichment**

Two things happen here, in sequence:

**(a) Collect more data about the lead**

The orchestrator gathers additional information from available sources — website visit history, social profiles, company data, internal CRM records, chat transcripts, past orders, external news. Internal history is always checked first before any external lookup.

**(b) Extract signal values (deterministic — no LLM)**

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

**Why not use an LLM to extract signals?** Because it keeps exactly one LLM call per lead (cost control), and makes the system debuggable — if a score is wrong, you can check whether the signal value was extracted incorrectly (enrichment bug) or evaluated incorrectly (scoring bug). Mixing the two makes it impossible to isolate problems.

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

This is the only LLM call in Pipeline 1. The orchestrator prepares the filled prompt and calls the Scoring Agent:

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

**What the Scoring Agent must return:**

```json
{
  "bucket": "HOT",
  "total_score": 84,
  "dimension_scores": {
    "fit": 8,
    "intent": 9,
    "engagement": 8,
    "behavioral": 6,
    "context": 7
  },
  "explanation_reasons": [
    "Requested pricing twice in 48 hours",
    "Visited product page 3 times this week",
    "Decision maker confirmed"
  ],
  "suggested_action": "Call today — high intent, strong fit",
  "confidence": 87
}
```

Dimension scores are always shown separately — they are never collapsed into one number. A lead that is high on intent but low on fit needs completely different action than the reverse.

Output schema: **`[TBD from S2 — especially the confidence field name and format]`**

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

**Confidence routing (runs after bucketing):**

| Confidence level | What happens | Why this threshold |
|---|---|---|
| ≥ 80% | Auto-assign bucket, write to output — no human needed | High confidence means the Scoring Agent had strong signal coverage and clear dimension separation — human review adds no value |
| 50–79% | Assign bucket but add a WARNING flag — salesperson can review | Moderate confidence means at least one dimension had weak or missing signals — the bucket is likely correct but worth a second look |
| < 50% | Do not auto-bucket — route to human review queue | Low confidence means the system cannot reliably distinguish between buckets for this lead — an automated assignment would be worse than no assignment |

**How these bands connect to quality metrics:** The split of leads across the three confidence bands is captured as the per-run confidence distribution metric (computed at the end of every Pipeline 1 run and written to `quality_snapshots`). A run where more than 50% of leads fall below 50% confidence triggers an alert — it signals that the Scoring Agent is uncertain about too many leads in the batch, which is an early indicator of prompt drift, signal extraction failures, or data quality problems. See [[analyses/governance-observability-layer]] Section 2.3 and [[analyses/scoring-quality-metrics]] for the full metric definitions.

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
7. Mark tenant as onboarding_complete
```

### 6.2 Pre-Flight Check Before Every Pipeline 1 Run

Before any lead is processed, the orchestrator checks:

```
Is tenant.onboarding_complete = true?
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
10. Format and deliver ranked lead cards to salesperson in chat
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
  "stage": "enriched | normalised | scored | bucketed",
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

From scored, one of three outcomes:
  → delivered        bucket assigned, SLA set, written to salesperson output
  → human_review     confidence < 50% OR scoring failed after retries

From any non-terminal stage:
  → failed           retries exhausted
```

**Terminal states:** `delivered`, `human_review`, `failed`

Exact field name and accepted string values: `[TBD from S1]`

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

If pipeline_stage is non-terminal AND last_updated is older than [TBD: 15–30 min]:
  → Resume. The previous run must have crashed.

If pipeline_stage is non-terminal AND last_updated is recent:
  → Skip. Another run is actively processing this lead right now.
```

Different leads never share mutable state, so leads processed in parallel never interfere with each other. Different tenants are fully isolated by `tenant_id`.

### 8.4 Crash Recovery

If the orchestrator crashes mid-run and restarts:

```
1. Query: all leads WHERE pipeline_stage is non-terminal
                      AND last_updated older than timeout_threshold
2. Reconstruct run context from pipeline_log using run_id
3. For each recoverable lead: re-enter Pipeline 1 at its current stage
4. Max 2 total retries per stage per lead
   → after 2 failures: mark the lead failed, move on
```

**One accepted tradeoff:** if the Scoring Agent was mid-call when the crash happened, it will be called again on recovery. This means one extra LLM cost for that lead. This is accepted — the `prompt_version` field in the lineage log means any scoring drift is visible and traceable.

**Idempotency requirement for S1 and S2:** every tool must be idempotent at its stage boundary. Calling the same tool twice with the same input must produce equivalent output and must not corrupt state.

### 8.5 Lineage Writes

The orchestrator writes a `pipeline_log` entry after **every tool call, at every stage, in both pipelines**. Individual tools never write lineage — only the orchestrator does.

Each entry records:

| Field | What it captures |
|---|---|
| `run_id` | Which run this entry belongs to |
| `lead_id` | Which lead (null for Pipeline 2 entries) |
| `agent_id` | Which tool produced this entry |
| `tenant_id` | Which tenant |
| `pipeline` | `onboarding` or `lead_processing` |
| `timestamp` | When this entry was written |
| `input_snapshot` | Exact input sent to the tool |
| `output_snapshot` | Exact output the tool returned |
| `duration_ms` | How long the tool took |
| `prompt_version` | Active prompt version — null for non-LLM tools |
| `confidence` | Confidence at this step — null before the scoring stage |
| `error` | Error message on failure, null on success |

Full schema: `[TBD from S1 — pipeline_log schema ticket]`

Concurrent writes across parallel leads are safe — each entry is unique on `(run_id, lead_id, stage)`.

**The lineage log is the primary data source for all scoring quality metrics.** The fields written here — especially `confidence`, `dimension_scores`, `prompt_version`, `signal_version`, and `fired_signals` — are exactly what the quality metric jobs in [[analyses/scoring-quality-metrics]] compute against. The orchestrator writing complete, accurate lineage after every stage is the prerequisite for every metric in that document. A missing lineage entry means a missing data point in the quality snapshot; a corrupt entry means a corrupt metric. The lineage write is not optional bookkeeping — it is the foundation of the measurement system.

| Lineage field | Quality metrics that depend on it |
|---|---|
| `confidence` | Per-run confidence distribution; C1, C2 (cross-run stability checks use confidence to filter) |
| `dimension_scores` | AP1, AP2 (bucket outcome rates require knowing which dimensions drove the score) |
| `prompt_version` | Attribution job (Step 1 of feedback loop) — identifies which prompt version is in wrong-bucket patterns |
| `fired_signals` | AP3 (completeness qualifier), C5 (signal contribution consistency spot-check) |
| `pipeline_stage` | Score Coverage Rate — denominator is leads that entered; numerator is leads that reached `scored` stage |

**Build lineage before adding the second LLM agent.** Retrofitting an audit trail across multiple running agents is extremely costly and error-prone.

---

## 9. What S1 and S2 Need to Deliver

The orchestrator sits between the data layer (S1) and the intelligence layer (S2). It cannot be fully built without interface contracts from both.

### Hard Blockers — orchestrator code cannot be written without these

| What is needed | Who delivers | Why the orchestrator needs it |
|---|---|---|
| `leads.pipeline_stage` — exact field name and all accepted string values | S1 | Orchestrator reads and writes this at every stage |
| `pipeline_log` — all field names and types | S1 | Orchestrator writes lineage after every tool call |
| Scoring Agent output JSON schema — especially the `confidence` field name and format | S2 | Orchestrator validates output, routes by confidence, logs the score |

### Soft Blockers — can be stubbed for now, but needed before final build

| What is needed | Who delivers |
|---|---|
| `tenant_config` mandatory field list | S1 |
| `signal_definitions` table schema | S1 |
| `human_review_queue` — confirmed as a table? what is the schema? | S1 |
| Persona object structure (Onboarding Agent output) | S2 |
| ICP object structure (ICP Agent output) | S2 |
| Signal Agent output schema | S2 |
| Signal `detection_rule` format and evaluation engine | S2 |

---

## 10. Open Decisions

| Decision | Owner |
|---|---|
| `leads.pipeline_stage` exact accepted values | S1 |
| `pipeline_log` schema | S1 |
| `signal_definitions` table schema | S1 |
| `human_review_queue` existence and schema | S1 |
| Scoring Agent output schema (incl. `confidence` field) | S2 |
| Signal `detection_rule` format + evaluation engine | S2 |
| Onboarding / ICP / Signal Agent output schemas | S2 |
| Scoring Agent concurrency cap | Team (recommend: 5) |
| Timeout threshold for concurrency guard | Team (recommend: 15–30 min) |
| Capability registry storage format | Team |
| Tool invocation envelope — confirm or revise the proposed shape | S1 + S2 |
| Disqualification rules per tenant | Per tenant |
| Bucket threshold calibration (after Month 1 data) | Team |
| Pipeline 2 check-in cadence | Team (suggest: 2 weeks or monthly) |
| Alert delivery channel (chat / email / both) | Team |

---

## 11. Confirmed Decisions

| Decision | Basis |
|---|---|
| Orchestrator is deterministic — makes no LLM calls | Team decision |
| Two-pipeline architecture: Pipeline 2 (setup) + Pipeline 1 (per lead) | Team decision 2026-04-19 |
| 4 LLM agents total (3 in Pipeline 2, 1 in Pipeline 1) | Team decision 2026-04-19 |
| One LLM call per lead (Scoring Agent only) | Team decision |
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
