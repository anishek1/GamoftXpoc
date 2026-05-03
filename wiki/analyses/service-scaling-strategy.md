---
type: analysis
question: "What are the best ways to scale the Ingestion Service, Orchestration+LLM Service, and Reporting Service for the Multi-Tenant Lead Intelligence Engine?"
date: 2026-04-24
tags: [scaling, multi-tenant, saas, architecture, ingestion, orchestration, llm, reporting]
sources_consulted:
  - "Tod Golding — Building Multi-Tenant SaaS Architecture (O'Reilly)"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/lead-pipeline-architecture]]"
  - "[[analyses/scoring-quality-metrics]]"
---

# Service Scaling Strategy

**Question:** What are the best ways to scale the three MVP services — Ingestion, Orchestration+LLM, and Reporting — for the Multi-Tenant Lead Intelligence Engine?  
**Date:** 2026-04-24  
**Reference framework:** Tod Golding, *Building Multi-Tenant SaaS Architecture* (O'Reilly)

---

## First: The Concepts You Need to Know

Before getting into the recommendations, here are the big ideas from the Golding book that everything below is built on. These are foundational concepts for any multi-tenant system — meaning any system where multiple separate customers (tenants) share the same software.

### The Pool Model — Shared Infrastructure

Imagine a shared office building. All the companies in the building use the same elevators, the same reception desk, the same parking lot. They have their own locked offices, but the building itself is one building.

That's the pool model. All tenants — Gamoft, Urvee Organics, Govmen — run on the same servers, the same database, the same worker processes. The system knows whose request belongs to whom by reading a tag (the `tenant_id`) stamped on every request that comes in.

**Why it's the right choice for MVP:** Three tenants running ~300 leads a day total is not a traffic problem. Building separate infrastructure per tenant (see Silo below) would cost 3× as much and take 3× as long to build. Pool is the only sensible starting point.

### The Silo Model — Dedicated Infrastructure

The opposite of pool. Each tenant gets their own completely separate database, their own servers, their own everything. Like giving each company their own separate building instead of one shared one.

**When it makes sense:** A very high-value enterprise customer who pays for it and needs guaranteed isolation — legally, contractually, or because they process sensitive data. At MVP with three POC tenants, this is not relevant. It's mentioned here so you know what "graduated to dedicated" means in the tiering section.

### The Bridge Model — Start Shared, Graduate High-Value Tenants

A hybrid of pool and silo. Basic/free tenants share infrastructure (pool). Premium/enterprise tenants get their own dedicated infrastructure (silo) when they grow to justify the cost.

**Why it matters for this system:** The long-term commercial answer for this product is almost certainly bridge. As Gamoft adds paying tenants, the highest-value ones can be offered a premium tier with dedicated resources. The architecture decisions you make at MVP should not make that future migration painful.

### Noisy Neighbor — The Core Risk at Our Scale

This is the most important concept for this specific system right now.

Imagine you live in an apartment building and one neighbour decides to throw a party at 2am every Friday. Even though you're in your own apartment, you can't sleep. That neighbour is a "noisy neighbor" — their behaviour on shared infrastructure hurts everyone else.

In software terms: if Gamoft runs a large batch of leads on a Friday afternoon, they could take up all 5 of the Scoring Agent's concurrent slots, leaving Urvee Organics and Govmen completely unable to process any leads until Gamoft's batch finishes.

**This is the number one scaling risk for this system.** Not volume — the system only handles ~300 leads a day. The risk is one tenant's spike starving the other tenants.

### Tiering — Giving Different Tenants Different Limits

The mechanism that controls noisy neighbor by design. You define "plans" — Basic, Standard, Premium — and each plan has explicit limits on how much of the shared infrastructure any one tenant can use at a time. A Standard tenant might be allowed 2 concurrent Scoring Agent calls. A Premium tenant gets 4. No single tenant can ever take everything.

**Why this is worth designing now:** Even if you don't enforce tiers in MVP, writing the per-tenant config structure now means you never have to do a painful migration later. The difference between "we designed for this" and "we didn't" is enormous.

### Metering — Tracking Who Used What

Counting per-tenant usage: how many LLM tokens Gamoft consumed this month, how many pipeline runs Urvee Organics triggered, how many API calls Govmen made.

**Two reasons this matters:**
1. **Cost attribution** — you need to know what each tenant actually costs you to run, especially for LLM API costs which can vary wildly.
2. **Tiering enforcement** — you can't enforce rate limits unless you're counting usage.

### Tenant Routing — How Every Request Gets Stamped with the Right Identity

This is the mechanism that makes the pool model safe. When a request comes into any service, the very first thing that happens is: extract the `tenant_id`, load the tenant's context, set a session variable that activates Postgres Row-Level Security (RLS). From that point forward, every database query is automatically scoped to that tenant's data only. The tenant can never see another tenant's leads.

In this system: JWT carries `tenant_id` → service reads JWT → sets `app.current_tenant_id` as a Postgres session variable → RLS activates automatically → every query is isolated.

**Why this must happen before any data is touched:** If routing is applied inconsistently — some code paths do it, some don't — you get data leakage between tenants. That's a catastrophic failure mode. The rule is zero exceptions.

---

## The Current Reality: Scale Is Not the Problem Yet

Before jumping into recommendations, it's worth being precise about what we're actually solving for.

The system processes ~300 leads per day across 3–5 tenants. That's about 12 leads per hour. By any measure, that's a small system. You could run it on a single server and it would be fine from a throughput perspective.

The *actual* risks are:
1. **Noisy neighbor** — one tenant's batch spike starves others (LLM concurrency is the bottleneck)
2. **LLM provider rate limits** — even if you have capacity, the provider (OpenAI, Groq) imposes per-minute token limits
3. **Read contention** — reporting queries hitting the same Postgres tables that Pipeline 1 is writing to, causing slowdowns in both directions

Every recommendation below is anchored to one of these three real risks. If a recommendation doesn't address one of them, it doesn't belong here.

---

## Service 1: The Ingestion Service

**What this service does:** Everything from the moment a lead event arrives until the lead is normalized and ready to be scored. That's: Data Gather (pulling raw data from channels), Lead Enrichment (deterministic signal extraction), and Normalise. The pipeline_stage goes from `fetched` → `enriched` → `normalised`.

**The scaling recommendation: Pool with tenant-tagged queues.**

### Why Pool?

Three tenants, ~300 leads a day. There is no case for separate infrastructure. One shared ingestion worker pool, with every task stamped with `tenant_id` at the moment it enters the queue.

### Recommendation 1: Use a Job Queue, Not Direct Processing [MVP]

**What it means:** When an event arrives, don't process it immediately in the web request. Push it onto a queue (a list of jobs to do) and let background workers pick them up.

**Why:** Without a queue, a sudden spike — say Gamoft imports 80 leads at once — blocks the entire ingestion service for every other tenant during that window. With a queue, the spike gets absorbed. Work happens at the rate the workers can handle it. The other tenants' leads sit in queue behind Gamoft's batch but are not blocked indefinitely — and with per-tenant queue priority (see below), you can ensure fair ordering.

**What to use:** Celery (Python), BullMQ (Node), or any standard job queue. The choice depends on the team's backend language (currently TBD).

### Recommendation 2: Stamp Every Job with tenant_id Immediately [MVP]

**What it means:** The very first field written when a job enters the queue is `tenant_id`. Every downstream step — enrichment, normalise — reads this tag and sets the RLS session variable before touching the database.

**Why:** This is non-negotiable. If any step in the pipeline touches the database without the RLS session variable set, there's a risk of cross-tenant data access. Stamping at intake and propagating through every step is the only safe pattern. The Golding book calls this "tenant context propagation" — it must be a first-class concern, not an afterthought.

### Recommendation 3: Per-Tenant Rate Limits on Channel Connectors [MVP]

**What it means:** Each connector (LinkedIn, WhatsApp, Instagram, website) has its own per-tenant daily/hourly call budget. Gamoft can't exhaust the LinkedIn API quota that Urvee Organics also depends on.

**Why:** Third-party APIs (LinkedIn especially) have account-level rate limits. If all tenants share one API credential pool, a single tenant burning through the daily LinkedIn quota locks out every other tenant for the rest of the day. Per-tenant limits prevent this and are also necessary to manage LinkedIn compliance risk.

**Note:** LinkedIn API compliance decision is still TBD. Per-tenant budgeting is the right design regardless of which decision is made.

### Recommendation 4: Lineage Writes Are Non-Negotiable — Don't Optimise Them Away [MVP]

**What it means:** After every stage (fetched, enriched, normalised), the orchestrator writes a lineage record. Don't be tempted to batch these writes or make them async to improve throughput.

**Why:** The entire measurement system — all 15 quality metrics, the 3 Global KPIs, the feedback loop — depends on complete, accurate lineage. The orchestrator writing lineage after every stage is the prerequisite for the entire governance layer. The orchestration-layer-spec calls this the "write-order rule": persist `pipeline_stage` to `leads` first, then write to `pipeline_log`. If you skip or delay lineage writes for performance, you break the measurement system. The volume at 12 leads/hour does not justify this trade-off.

### Recommendation 5: Idempotent Enrichment [Design now, implement before adding channels]

**What it means:** If the enrichment step runs twice for the same lead (e.g., a crash followed by a retry), the second run produces exactly the same result and doesn't double-write to the database.

**Why:** Queues and retries are a pair. When you add a job queue, you also add automatic retry on failure. If enrichment is not idempotent, retries cause corrupted data — duplicate signal extractions, duplicate lineage records, leads stuck in wrong states. Design enrichment as a pure function of the lead data: same input, same output, no side effects on repeated runs.

---

## Service 2: The Orchestration + LLM Service

This service has two internal parts that should be understood separately, even if they're deployed together at MVP:

- **Orchestration controller:** The stateful brain. It reads `pipeline_stage`, decides what to do next, calls tools in sequence, writes lineage. Deterministic — no LLM.
- **LLM wrapper / prompt execution:** The `score_lead()` call. Takes the enriched, normalised lead + the tenant's signal definitions, calls the LLM (Sonnet), returns a structured `ScoringOutput`. Runs for every lead on both the DM path and the Lead Ad path. On the DM path only, a second cheaper Haiku call (Message Parser) fires earlier in the pipeline.

### The Scaling Recommendation: Pool with Per-Tenant Concurrency Caps

### Recommendation 6: Change the Concurrency Cap from Global to Per-Tenant [MVP — Key Architectural Win]

**What this means today:** The current design says "max 5 concurrent Scoring Agent calls globally." That means all 3 tenants share a pool of 5 slots.

**The problem:** If Gamoft submits a batch of 5 leads at once, they fill all 5 slots. Urvee Organics and Govmen cannot score a single lead until Gamoft's batch completes. This is a textbook noisy neighbor failure.

**The fix:** Replace the global cap with a per-tenant cap. With 3 tenants and a cap of 2 per tenant, you have at most 6 concurrent Scoring Agent calls — slightly more total load, but *no single tenant can ever starve the others*. At 12 leads/hour this is trivially manageable.

**How to implement:** A semaphore keyed on `tenant_id`. Before calling `score_lead()`, acquire the semaphore for that tenant. If 2 calls are already running for that tenant, the third waits in queue. Takes about 20 lines of code. This is the single most important change to make in this service from a Golding multi-tenant perspective.

**Why the current global cap is wrong:** Golding is explicit that resource limits in a shared system must be scoped per tenant, not globally. A global cap protects the LLM provider from overload but does nothing to protect tenants from each other.

### Recommendation 7: Store Per-Tenant LLM Config in the Tenant Record [MVP]

**What it means:** The tenant's configuration record stores: which LLM model to use, which prompt version is active for this tenant, the concurrency cap, the token budget per lead. The Scoring Agent reads this config at call time — it does not hardcode anything.

**Why:** Two reasons. First, different tenants may legitimately need different models (a high-value tenant might pay for GPT-4; a basic tenant uses a cheaper model). Second, when you want to recalibrate a tenant's configuration — after Month 1 when you have real data — you update one config record, not code. The orchestration-layer-spec's "system proposes / human approves" principle for config changes depends on this.

### Recommendation 8: Use the LLM's System Message for Prompt Caching [MVP]

**What it means:** The Scoring Agent's prompt has two parts: the static part (the scoring rubric, the signal definitions, the output schema instructions) and the dynamic part (the specific lead's data). Put the static part in the system message, the dynamic part in the user message.

**Why:** OpenAI and Anthropic both cache prompt prefixes — specifically the system message — across calls. If 20 leads are being scored in a row for Gamoft, the LLM provider reuses the cached system message for calls 2 through 20. This cuts token costs and latency significantly. The intelligence layer design spec already calls for this. It's a free win that requires zero extra infrastructure — just structure the prompt correctly.

### Recommendation 9: Timeout and Fail Loudly [MVP]

**What it means:** The Scoring Agent has a 60-second hard timeout (already locked in the design). If the LLM call doesn't return in 60 seconds, the lead's `pipeline_stage` is set to `human_review` with `reason: scoring_failed`, a lineage record is written with the failure.

**Why:** Without a hard timeout, a slow or hung LLM call holds a concurrency slot indefinitely. With a per-tenant cap of 2, one hung call means that tenant is operating at 50% scoring capacity until someone notices. The 60-second timeout ensures hung calls are released quickly and the failure is visible in the lineage log, which feeds the monitoring alerts. The intelligence layer spec already mandates this — the implementation must enforce it.

### Recommendation 10: Crash Recovery via pipeline_stage [MVP]

**What it means:** The orchestration controller reads `pipeline_stage` from Postgres at startup and on every retry. If the server crashes mid-run, the next pickup reads the current stage and resumes from there — it never re-runs completed stages.

**Why:** This is the crash safety guarantee that the orchestration-layer-spec defines as non-negotiable. The write-order rule (write `pipeline_stage` to `leads` first, then write to `pipeline_log`) ensures that on a crash, the state is always recoverable. This is not a future concern — it must work from day one, because crashes happen.

---

## Service 3: The Reporting Service

**What this service does:** Serves the REST API for leads, lineage, and quality data. Powers the role-scoped dashboards that salespeople and team leads use. Runs scheduled reports. Everything in the delivery layer that is read-heavy.

**The scaling recommendation: Enforce a read/write split. The reporting service must never compete with Pipeline 1.**

### Recommendation 11: quality_snapshots Is the Read Model — Make It a Hard Rule [MVP]

**What it means:** Every dashboard query, every report, every API response for quality metrics reads from the `quality_snapshots` table — not from `leads`, `pipeline_log`, or `lineage_record`. The `quality_snapshots` table is pre-computed by scheduled SQL jobs (per-run, weekly, monthly) and is the single authoritative read surface for all metric data.

**Why this is the most important rule for the reporting service:** `pipeline_log` is written to constantly by Pipeline 1 — every stage of every lead writes a lineage record. If a dashboard query hits `pipeline_log` directly to aggregate metrics, it competes with Pipeline 1 writes, causes lock contention, slows down active lead processing, and degrades the data you need for dashboards all at the same time. The `quality_snapshots` design was specifically created to prevent this. Codify it as an enforced rule: no dashboard or report query touches raw pipeline tables.

### Recommendation 12: Add a Postgres Read Replica for All Reporting Queries [Design now, deploy when read load warrants]

**What it means:** Postgres supports read replicas — a second database server that receives a copy of all writes in real time and is available for read queries only. Point the reporting service at the read replica; Pipeline 1 writes to the primary.

**Why:** At MVP with ~300 leads/day, read contention is unlikely to be a crisis. But it's worth designing for now because adding a read replica later requires changing connection strings — a one-line config change if the architecture already separates read and write connections. If you don't design for it now, adding it later means refactoring how both Pipeline 1 and the reporting service connect to the database.

**Practical note:** Even before adding a physical read replica, configure the reporting service to use a separate connection string environment variable (e.g., `DATABASE_READ_URL`). In MVP, point it at the same database. When you add the replica, change one variable.

### Recommendation 13: RBAC Scoping Must Be Enforced in the Reporting Service, Not Just the Frontend [MVP]

**What it means:** The four roles (admin, team_lead, salesperson, viewer) have different views of the data. A salesperson sees only their own leads. A team lead sees all leads for their tenant. An admin sees tenant-level config. This scoping must be enforced in the API layer — not just hidden in the frontend UI.

**Why:** Frontend-only access control is not access control. Any user with a valid JWT and a REST client can bypass the frontend and call the API directly. If the API doesn't enforce role scoping, any salesperson can pull every other salesperson's leads. RLS handles tenant isolation (cross-tenant leakage). RBAC handles role isolation (within-tenant privilege escalation). Both must be enforced server-side.

### Recommendation 14: Pre-Compute Reports — Never Generate on Request [MVP for scheduled reports]

**What it means:** Scheduled reports (daily digest, weekly summary) are generated by a background job and stored. When a user requests a report, they receive the pre-generated file — not a live query.

**Why:** Report generation typically involves aggregating weeks or months of lineage and metric data. Running that aggregation on every request is expensive and slow. It competes with the real-time read path (dashboards) and with Pipeline 1 writes. Pre-computing reports on a schedule (midnight, Sunday night) means the generation cost is paid once, at a low-traffic time, and the result is instant to serve. The delivery-integration-layer spec already identifies `report_job` and `report_artifact` as S1 delivery entities — use them.

### Recommendation 15: Tenant-Scoped Metering for LLM Cost Attribution [Design now, display later]

**What it means:** Every Scoring Agent call records: which tenant triggered it, which model was used, how many input tokens, how many output tokens, the cost in USD. This is written to a `usage_record` or similar entity. The reporting service exposes this per tenant.

**Why:** LLM costs are the largest variable operating cost in this system. Without per-tenant metering, you can't answer "what does it cost to run Urvee Organics?" — which means you can't price the product correctly, you can't bill tenants fairly, and you can't make decisions about which model to use for which tenant. Golding treats metering as a foundational requirement for any commercially viable multi-tenant SaaS product. Log the cost at call time. Display it later when the reporting surface is built.

---

## Tiering: The Framework to Build Toward

The table below defines what per-tenant resource limits should look like across three tier levels. You don't need to enforce all of these at MVP — but you should write the per-tenant config schema to support them from day one, so that activating a tier is a config change, not a code change.

| Limit | Basic (MVP default) | Standard | Premium |
|---|---|---|---|
| Concurrent Scoring Agent calls | 2 | 3 | 5 |
| Pipeline 1 runs per hour | 20 | 50 | Unlimited |
| LLM token budget per lead | 4,000 | 8,000 | Unlimited |
| API requests per minute (reporting) | 30 | 100 | 500 |
| Scheduled reports | None | Weekly digest | Daily digest + custom |
| Read path | Shared replica | Shared replica | Dedicated replica |
| Infra model | Pool | Pool | Pool or Silo |

**Why define this now?** Because the cost of retrofitting per-tenant config into a system that was built without it is very high. If you write `tenant_config` as a flat record with limit fields from the start, activating tiering is just populating those fields. If you don't, you have to refactor every place in the codebase that currently hardcodes a global limit.

---

## Locked Constraints Cross-Check

Every recommendation above has been checked against the locked design decisions in the project. Nothing below conflicts with anything locked.

| Locked constraint | How the scaling strategy respects it |
|---|---|
| LLM calls per lead | Per-tenant concurrency cap applies to the Scoring Agent (Sonnet, all paths). On the DM path, a second Haiku call (Message Parser) also fires at lower cost. All other stages are deterministic — no LLM, no rate limit risk. |
| Governance failure must never halt pipelines | All metering, cost logging, and usage tracking run as fire-and-forget events. If the metering write fails, Pipeline 1 continues. |
| Delivery failures never roll back Pipeline 1 | The score is persisted to `leads` before delivery is attempted. Scaling the reporting service does not touch this guarantee. |
| System proposes / human approves on config changes | Tiering limit changes and concurrency cap changes require team lead or admin approval. The per-tenant config record is the surface where these are applied. |
| Lineage write-order rule (leads first, then pipeline_log) | All scaling recommendations preserve this write order. Idempotency recommendation explicitly requires that retries do not double-write lineage. |
| pipeline_stage transitions are the crash safety guarantee | Crash recovery recommendation (Recommendation 10) is a direct implementation of this guarantee, not an addition to it. |
| RLS + JWT + 4-role RBAC | Tenant routing (Recommendation 2) and RBAC enforcement (Recommendation 13) are implementations of the existing security model, not changes to it. |

---

## The Five Changes That Move the Needle Now

If you only do five things from this entire document, do these:

1. **Make the concurrency cap per-tenant, not global.** (Rec 6) — Prevents noisy neighbor on the most expensive resource in the system. 20 lines of code.

2. **Write the per-tenant config schema with limit fields from day one.** (Rec 7, Tiering section) — The cost of retrofitting this later is very high. The cost of doing it now is one database table with a few extra columns.

3. **Stamp every queue job with tenant_id at intake.** (Rec 2) — Non-negotiable for safe pool-model operation. One field, always present, always propagated.

4. **Enforce the quality_snapshots rule — no dashboard query touches raw pipeline tables.** (Rec 11) — Prevents read/write contention. Already designed; just needs to be enforced as a code review rule.

5. **Log LLM token usage per tenant per call.** (Rec 15) — You will need this data. Collecting it from day one costs almost nothing. Reconstructing it retroactively is impossible.

---

## Answer / Finding

The system runs at low volume (~300 leads/day) but faces three real scaling risks: noisy neighbor on LLM concurrency, LLM provider rate limits, and read/write contention in Postgres. The correct isolation model for all three services at MVP is the pool model — shared infrastructure, tenant-tagged at intake.

The single most important architectural change is making the Scoring Agent concurrency cap per-tenant (not global). The current design's global cap of 5 allows one tenant to starve all others during a batch run. A per-tenant cap of 2 costs nothing to implement and eliminates the core noisy neighbor risk.

The reporting service's scaling answer is already built into the data model: the `quality_snapshots` table is the read model. Codifying the rule that no reporting query touches raw pipeline tables, and separating read/write connection strings from day one, keeps the reporting service from competing with Pipeline 1.

The long-term commercial model is a bridge architecture: all current tenants in pool, high-value future tenants graduated to silo. Building per-tenant config, per-tenant limits, and per-tenant metering from the start makes that graduation a config change rather than a rewrite.

## Caveats & Gaps

- **LLM provider — RESOLVED 2026-05-03** — Anthropic Claude Sonnet 4.6 (primary), OpenAI GPT-4o via LiteLLM (fallback). Per-tenant concurrency limits should be calibrated against Anthropic's account-level rate limits.
- **Backend language is TBD** — queue technology (Celery, BullMQ, etc.) depends on this choice.
- **Signal detection_rule format — RESOLVED 2026-04-28.** Named extractor + params model. Enrichment code can now be written. Scaling design for the enrichment service is unaffected. See [[analyses/signal-detection-rule-spec]].
- **Alert thresholds for all monitoring** — all to be set after Month 1 baseline. The monitoring infrastructure should be wired from day one; the thresholds get filled in later.

## Follow-up Questions

- LLM provider is resolved (Anthropic Claude). Token budget defaults and tiering rate limit numbers should now be calibrated against Anthropic's account limits.
- What is the backend language? This determines the queue technology for Recommendations 1 and 3.
- Should the per-tenant concurrency cap be configurable per-tenant from day one, or start as a hardcoded default (2) with a config override path ready?
- Is there a timeline for when the first paying (non-POC) tenant is expected? That determines urgency of the bridge model readiness.
