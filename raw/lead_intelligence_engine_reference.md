---
title: Multi-Tenant Adaptive Lead Intelligence Engine
version: v2.0 (reference doc, not PRD)
status: Pre-planning — source of truth for ticket-driven discussions
owner: Anishekh
org: Gamoft
last_updated: 2026-04-14
tags: [lead-intelligence, agentic, multi-tenant, reference, poc-planning]
---

# Multi-Tenant Adaptive Lead Intelligence Engine — Master Reference

> **This is not a PRD.** This is the single source of truth compiled from all pre-planning discussions. It captures every decision made, every reasoning thread, and every open question. Each section is ticket-ready — open a ticket against a section, discuss with team, update the `[TBD]` markers with decisions, and move on.

---

## 00 — How to Use This Document

### Purpose
This document exists to feed Claude terminal and Obsidian during the ticket-by-ticket POC planning phase. After ~100 tickets of discussion, final specification documents will be derived from the resolved TBDs in this file.

### Status markers — what every tag means
- `[LOCKED]` — Decided in chat. Do not re-open without strong cause.
- `[TBD]` — To be decided in a dedicated ticket. Not yet discussed.
- `[RESEARCH NEEDED]` — Requires external lookup (API docs, benchmarks, pricing).
- `[TEAM INPUT]` — Needs collective decision, not solo call.
- `[DEFERRED]` — Intentionally pushed to Sprint 2-3 (Add-ons 6/7/8).
- `[ASSUMPTION CHECK]` — Something implied in chat but never explicitly confirmed. Flag before committing.

### How to ingest
Drop this file into your raw directory. Ask Claude `ingest lead_intelligence_engine_reference.md`. Then query by section number or tag.

### Navigation
Jump by section number (01 through 20). All section headers use `## NN —` format for clean Ctrl+F.

---

## 01 — System Overview (One Page)

### What this is
A production-grade agentic pipeline that ingests leads from multiple channels (WhatsApp, Instagram, Website), enriches them with internal and public data, scores them contextually using tenant-specific personas via an LLM, and delivers ranked buckets (HOT/WARM/COLD) with explanations and recommended actions — all inside a chat interface where salespeople already work.

### Who it serves
Three tenants in the POC: **Urvee Organics** (B2C), **Gamoft** (B2B self-tenant), **Govmen** `[TBD — profile unknown]`.

### What makes it different from a CRM
- Multi-tenant with isolated personas (same lead scores differently per tenant)
- LLM-driven scoring (not rule-based weighted sums)
- User never sees agents, signals, or technical surfaces
- Full lineage log for every transformation
- Confidence as first-class user-visible field

### Version scope
- **v2.0 (this doc):** Add-ons 1-5 embedded, 7-phase pipeline, one true LLM agent
- **v2.1+ (deferred):** Add-ons 6-7-8 — adaptive signal lifecycle (see Section 17)

---

## 02 — Core Design Principles

Five principles drive every architectural decision. Every ticket discussion should be tested against these.

### P1 — User lives in the chat interface
Users never see agents, signal names, schemas, or technical surfaces. The orchestrator is the only thing they interact with. When they tap feedback, the system silently routes it to the right subsystem.

### P2 — LLM only where judgment is needed
Only ONE true LLM agent in the entire pipeline (Agent E). Everything else is deterministic tooling. This keeps costs predictable, execution fast, debugging simple.

### P3 — Every tenant has an isolated persona
Persona drives prompt construction, scoring priorities, and output formatting. Same lead → different score across tenants is by design, not a bug.

### P4 — Confidence is as important as the score
Two leads scoring 85 are not the same if one has 90% confidence and the other 40%. Confidence is a user-visible field and drives routing (auto-bucket vs human review).

### P5 — Every transformation writes to the lineage log
Per lead, per agent step: input snapshot, output snapshot, prompt version, confidence, timestamp. Non-negotiable. Build before second agent.

---

## 03 — Pipeline Overview

### The 8-stage flow
```
User Input
  → Orchestrator: Intent Detection + Persona Load
    → Agent A: Source Fetch (parallel)
      → Agent B: Data Gather (internal + external)
        → Agent C: Normalise (unified schema)
          → Agent D: Prompt Construction (persona-injected)
            → Agent E: LLM Enrichment + Scoring
              → Orchestrator: Final Output (bucketing, SLA, decay, feedback)
```

### Component classification [LOCKED via Add-on 1]
| Component | Type | Rationale |
|---|---|---|
| Orchestrator | TOOL | Workflow engine, no reasoning needed |
| Intent Classification | TOOL | Deterministic mapping |
| Persona Load | TOOL | DB fetch |
| Agent A (Source Fetch) | TOOL | API calls, dedup, rate limits |
| Agent B (Data Gather) | TOOL | DB queries + permitted public fetches |
| Agent C (Normalise) | TOOL | Schema transformation |
| Agent D (Prompt Build) | TOOL | Template assembly |
| **Agent E (LLM Scoring)** | **LLM AGENT** | **Holistic lead judgment** |
| Output/SLA/Decay/Feedback | TOOL | Rules + jobs |

**Total: 1 LLM agent, 8+ tools.**

### Status transitions a lead goes through
```
captured → fetched → gathered → normalised → prompt_ready → enriched → delivered
                                                            ↓
                                                  (or: human_review)
```

---

## 04 — The 5 Committed Add-ons (v2.0)

Each add-on below has its own deep-dive section later. This is the summary table.

### Add-on 1 — Agent vs Tool Classification `[LOCKED]`
- **What:** Tag every component as `LLM_AGENT` or `TOOL`
- **Why:** Cost, speed, reliability, debuggability
- **Impact:** Only Agent E is LLM; all others deterministic
- **Source:** Derived from manager's chat conversation

### Add-on 2 — Persona Layer as first-class entity `[LOCKED]`
- **What:** Rich per-tenant persona schema beyond simple `tenant_config`
- **Why:** Generic scoring doesn't differentiate B2C organic buyers from B2B IT prospects
- **Impact:** New `personas` table; Phase 04 injects persona into prompts
- **Deep dive:** Section 15

### Add-on 3 — Confidence as first-class output field `[LOCKED]`
- **What:** Promote confidence from internal routing signal to user-visible field
- **Why:** Score alone is not actionable without trust signal
- **Impact:** Every lead card shows `score + confidence`; routing uses confidence thresholds

### Add-on 4 — Disqualification + Score Decay + Action SLAs `[LOCKED]`
- **4a Disqualification:** Critical overrides before bucketing (serviceability=0 hard-caps at 50, wrong geo -30, non-decision-maker -40, student/spam → 0)
- **4b Score Decay:** Background job — no activity 7d=-10, no response 14d=-20, dormant 30d → cold
- **4c Action SLA:** HOT=24h, WARM=2-3d, COLD=weekly nurture; stale HOT triggers alert

### Add-on 5 — State Store Schema `[LOCKED]` (field-level `[TBD]`)
- **What:** Formalized Postgres schema with new `personas` and `signal_definitions` tables
- **Why:** Prevents premature infra complexity (no Kafka/Redis at current scale)
- **Impact:** All state lives in Postgres initially
- **Deep dive:** Section 13

---

## 05 — Phase 00: Input, Intent Detection, Persona Load

### 05.1 Raw User Message Reception `[LOCKED concept]`
User types in chat. Examples captured in chat:
- "check my leads"
- "who should I call today"
- "any new leads from instagram"
- "what happened with lead xyz"

**Rule:** Never pass raw user message directly to subagents. Orchestrator translates first.

### 05.2 Intent Classification [TOOL] `[LOCKED concept]`
Maps vague input → structured task with scope and filter.

Example mappings from chat:
- "check leads" → `task: lead_enrichment, scope: all_pending`
- "who to call" → `task: lead_enrichment, filter: hot_bucket`
- "new instagram leads" → `task: lead_enrichment, source: instagram`

**Edge case rule [LOCKED]:** If intent confidence below threshold, NEVER guess. Present 2-3 quick-action options and wait.

**Open:** `[TBD]` — exact classification implementation (regex/rules vs small LLM vs hybrid)

### 05.3 Persona + Tenant Config Load [TOOL] `[LOCKED — Add-on 2]`

**Config loaded per tenant:**
- Active source channels (WhatsApp, Instagram, Website)
- Scoring weights (fit, intent, engagement, behavior, context)
- Hot/warm/cold thresholds
- Output format and language preference
- Rate limit quotas for third-party APIs
- **NEW:** Full persona object (see Section 15)

**Edge case rule [LOCKED]:** If tenant config OR persona is missing or malformed → HALT pipeline and alert. Never proceed with defaults. Wrong config silently produces wrong scores for every lead in the run.

### 05.4 Confirmation Before Execution `[LOCKED]`
Plain-English preview before consuming API quota:
> "I'll enrich 12 new leads from WhatsApp and Instagram for Urvee. Takes ~2 minutes. Go ahead?"

**Rules:**
- First-time or scope-changed runs → show confirmation
- Scheduled/repeat runs → skip confirmation

### 05.5 Output of Phase 00
- Status: `intent_ready`
- Lineage entry written

### Open tickets for Phase 00
- `[TBD]` — Intent classifier implementation (rules vs LLM)
- `[TBD]` — Confirmation UX wording per tenant language preference
- `[TBD]` — Schedule/trigger system for non-interactive runs

---

## 06 — Phase 01: Agent A — Source Fetch [TOOL]

### 06.1 Parallel Source Connections `[LOCKED]`
Three channels fetched in parallel (sequential wastes time and blocks pipeline):
- **WhatsApp Business API** — new messages, inquiries, chat threads
- **Instagram Graph API** — DMs, story replies, comment leads
- **Website** — form submissions, chat widget, landing page captures

**Rule:** Credentials per tenant from secrets vault. Never hardcoded. Scoped + rotated independently.

**Open:**
- `[RESEARCH NEEDED]` — Exact API scopes needed for each (Meta Business Discovery requires specific permissions per chat)
- `[TBD]` — Secrets vault choice (AWS Secrets Manager / HashiCorp Vault / other)

### 06.2 Rate Limit Management `[LOCKED concept]`
- Per-tenant quota tracked in shared rate limit table
- Before each API call, check remaining quota
- If near limit, queue request for next available window
- Log all quota usage with timestamp and tenant ID

**Edge case rule [LOCKED]:** If API rate limit fully exhausted mid-run, partial results saved to state store with status `incomplete_fetch`. Pipeline continues with what it has. User notified which sources were incomplete.

**Open:**
- `[TBD]` — Exact quota numbers per API per tenant
- `[TBD]` — Rate limit table schema (fields not locked)

### 06.3 Source Failure Handling `[LOCKED]`
Explicit behavior per scenario:
- **API timeout** → retry once after 3 seconds, then mark source as unavailable
- **Auth failure** → alert tenant admin immediately, skip that source
- **Empty response** → mark source as "no new leads", continue
- **All sources fail** → halt pipeline, notify user with reason

**Principle:** Graceful degradation. Failed WhatsApp should not prevent website leads from being enriched.

### 06.4 Deduplication `[LOCKED]`
- **Match priority:** phone (primary) → email (secondary) → name + location (fallback)
- **Match found** → merge records, preserve all source tags
- **Uncertain match** → flag for human review, do NOT auto-merge

**Edge case [LOCKED]:** Two people with same phone number (shared family). Never auto-merge without high-confidence match on at least 2 identifiers.

**Open:**
- `[TBD]` — "High-confidence match" threshold (exact algorithm)
- `[TBD]` — Human review queue UX

### 06.5 Output of Phase 01
- Raw lead payload per source, tagged with: `source_id, tenant_id, timestamp, channel, raw_content`
- Written to `leads` state table
- Status: `fetched`

### Open tickets for Phase 01
- API credential management system
- Rate limit table design
- Deduplication algorithm specification
- Incomplete fetch notification UX

---

## 07 — Phase 02: Agent B — Data Gather [TOOL]

### 07.1 Internal History Lookup `[LOCKED]`
**ALWAYS runs before any external enrichment.** Faster, more reliable, more relevant than public data.

Sources checked:
- CRM — previous interactions, proposals, pipeline stage
- Order database — past purchases, frequency, basket size
- WhatsApp history — previous conversation threads
- Support tickets — complaints, resolutions, satisfaction

**Rule:** Never skip even if the lead "looks new."

**Open:**
- `[TBD]` — CRM integration targets (which CRMs to support in v2.0?)
- `[TBD]` — Order database schema per tenant (Urvee has e-commerce; Gamoft may not)
- `[ASSUMPTION CHECK]` — Assumed internal data exists; for net-new tenants this may be empty

### 07.2 Public Profile Verification `[LOCKED concept]`
Differs by business type:

**B2C (Urvee):**
- Instagram profile
- Facebook
- Review history

**B2B (Gamoft):**
- LinkedIn company page
- Job boards
- Industry news

**Both:**
- Phone verification via carrier lookup (optional)

**Edge case [LOCKED]:** Lead has no public profile. NOT necessarily bad. Many valid B2C buyers are off social media. Do not penalize heavily. Mark as `unverified`, weight other signals more.

**Open:**
- `[RESEARCH NEEDED]` — LinkedIn API access strategy (official Pages Data Portability vs scraping — chat flagged compliance concerns)
- `[RESEARCH NEEDED]` — Instagram Business Discovery API scope for accessing non-owned accounts
- `[TBD]` — Fallback behavior when public verification fails

### 07.3 Signal Collection `[LOCKED concept]`
Five categories of signals gathered per lead:
- **Digital footprint** — pages visited, content consumed, form depth
- **Intent signals** — pricing request, urgency language, demo request
- **Behavioral** — response speed, revisit frequency, reorder pattern
- **Contextual** — location, city tier, seasonality, festival timing
- **Network** — referrer, family cluster, shared account signals

**Rule [LOCKED]:** Only collect signals that are observable, relevant, and verifiable. Do not invent. If unconfirmable, mark as `assumed` with low weight. Never treat assumptions as facts in scoring.

**Open:**
- `[TBD]` — Exact signal taxonomy (the specific signal names — this becomes `signal_definitions` foundation for Add-on 7 deferred)
- `[TBD]` — How signals tag with `source + confidence` at field level

### 07.4 Output of Phase 02
- Enriched lead object with signals tagged, source-attributed, confidence-rated
- Status: `gathered`

### Open tickets for Phase 02
- Internal data source inventory per tenant
- Public API compliance strategy (LinkedIn, Instagram)
- Signal taxonomy definition
- Signal confidence computation method

---

## 08 — Phase 03: Agent C — Normalise [TOOL]

### 08.1 Schema Unification `[LOCKED]`
WhatsApp returns chat object, Instagram returns DM object, website returns form submission. Structurally different. Must become one schema.

**Normalization rules captured in chat:**
- Phone → E.164 format (`+91XXXXXXXXXX`)
- Name → Title Case, strip emojis
- Location → city, state, country, tier (1/2/3)
- Date/time → ISO 8601 UTC
- Product interest → map to internal product taxonomy

**Open:**
- `[TBD]` — Internal product taxonomy per tenant (Urvee has oil categories; Gamoft has service lines)
- `[TBD]` — Unified lead schema (exact field list for `leads` table)

### 08.2 Data Quality Scoring `[LOCKED]`
Every lead bucketed by completeness:
- **Complete** (80-100%): all mandatory fields present and verified
- **Partial** (50-79%): some fields missing, most verifiable
- **Sparse** (<50%): significant gaps, enrichment confidence low

**Edge case [LOCKED]:** Lead with only phone number (common from WhatsApp cold inquiries). Mark as `sparse`. Proceed — do not discard. A phone number is enough to begin enrichment. Flag confidence as low.

**Open:**
- `[TBD]` — Exact mandatory field list per tenant type (B2B vs B2C)

### 08.3 Conflict Resolution `[LOCKED]`
Rules for when a lead has different phone numbers on WhatsApp vs website:
- Most recent data wins for contact details
- Internal CRM data overrides external self-reported data
- If conflict unresolvable → flag for human review, store BOTH values

**Rule:** Every conflict resolution decision is logged for audit purposes.

### 08.4 Output of Phase 03
- Clean, unified lead record conforming to universal schema
- Completeness score attached
- Conflicts documented
- Status: `normalised`

### Open tickets for Phase 03
- Universal lead schema specification
- Product taxonomy per tenant
- Conflict resolution rule refinement
- Human review UX for conflicts

---

## 09 — Phase 04: Agent D — Prompt Construction [TOOL]

### 09.1 Prompt Template Registry `[LOCKED concept]`
Prompts are code. Versioned, reviewable, rollback-capable.

**Registry contents per template:**
- `template_id, version, use_case, tenant_applicable`
- Base structure: role, context, task, output schema, constraints
- Tenant overrides: tone, language, scoring emphasis
- Version history with changelog

**Rule [LOCKED]:** Every agent call MUST log which prompt version was used. Needed for reproducibility and debugging.

**Open:**
- `[TBD]` — Prompt registry storage (DB table vs Git repo vs both)
- `[TBD]` — Prompt review/approval workflow

### 09.2 Prompt Assembly with Persona Injection `[LOCKED — Add-on 2 integration]`
Final prompt combines:
1. Base template for task type
2. **Tenant persona context** (industry, target roles, priority signals, negative signals) — NEW in v2.0
3. Normalised lead data
4. Output JSON schema specification
5. Confidence instruction (explicit)

**Confidence instruction [LOCKED wording concept]:**
> "Where data is insufficient, state confidence as low and do not infer. Return null for missing fields rather than guessing."

This is primary hallucination control.

**Open:**
- `[TBD]` — Exact prompt templates per tenant (B2B vs B2C base versions)
- `[TBD]` — Persona context formatting in prompt (natural language vs JSON vs hybrid)
- `[TEAM INPUT]` — Few-shot examples per tenant

### 09.3 Dry Run Mode `[LOCKED concept]`
Test new prompts without production risk.

**Behavior:**
- Executes full pipeline end-to-end
- Logs all outputs to `dry_run` table, NEVER production table
- Returns preview of what would have been written
- No API side effects, no state changes

**Open:**
- `[TBD]` — Dry run UX (CLI command? Admin UI button? Both?)
- `[TBD]` — Dry run result comparison tooling (diff with live outputs)

### 09.4 Output of Phase 04
- Fully assembled, versioned prompt payload ready for Agent E
- Includes: prompt text, output schema, confidence instructions, tenant context
- Status: `prompt_ready`

### Open tickets for Phase 04
- Prompt template specification (base + tenant overrides)
- Prompt registry schema
- Dry run tooling
- Few-shot example library

---

## 10 — Phase 05: Agent E — LLM Enrichment & Scoring [LLM AGENT]

**The only true LLM agent in the pipeline.** This is where judgment happens.

### 10.1 Multi-Dimensional Scoring `[LOCKED]`
Five dimensions (weights configurable per tenant via persona):
- **Fit Score** — industry match, role relevance, serviceability
- **Intent Score** — urgency signals, price requests, comparison behavior
- **Engagement Score** — response speed, touchpoint frequency, repeat contact
- **Behavioral Score** — reorder history, past conversion, buying pattern
- **Context Score** — timing, location, seasonal relevance, external triggers

**Rule [LOCKED]:** Never combine all five into one magic number without showing the breakdown. The breakdown IS the value. A lead high on intent but low on fit needs different action than high fit low intent.

**Open:**
- `[RESEARCH NEEDED]` — LLM provider choice (OpenAI / Anthropic / Groq / NVIDIA NIM — chat mentions researching NIM for budget)
- `[TBD]` — Temperature setting (chat recommends low but no specific value)
- `[TBD]` — Model size per tenant (premium model for high-value B2B vs cheaper for high-volume B2C?)

### 10.2 Disqualification Gate `[LOCKED — Add-on 4a]`
Applied BEFORE bucketing. Critical parameter overrides from chat:
- `serviceability = 0` → hard cap score at 50 (or mark as disqualified)
- `wrong geography` → -30 points
- `non-decision-maker` → -40 points
- `student / spam / irrelevant` → auto-discard (score 0)

**Rule:** These are not just negative signals — they are gates that prevent wrong leads from reaching HOT bucket.

**Open:**
- `[TBD]` — Complete disqualification rule set per tenant
- `[TBD]` — How disqualified leads are presented to user (hidden? flagged? shown with reason?)

### 10.3 Confidence Threshold and Human-in-the-Loop `[LOCKED — Add-on 3]`
Confidence is first-class output field.

**Routing logic [LOCKED]:**
- Confidence ≥ 80% → auto-bucket, write to output
- Confidence 50-79% → bucket with warning flag, suggest human review
- Confidence < 50% → route to human review queue, do NOT auto-bucket

**Edge case [LOCKED]:** Human review queue fills up and nobody reviews. Set SLA alert — if lead in human review > N hours without action, escalate to team lead. Stale unreviewed leads as bad as wrong scores.

**Open:**
- `[TBD]` — Exact N for stale review SLA
- `[TBD]` — Human review UX surface (in-chat vs separate admin screen)
- `[TBD]` — How confidence is calculated (self-reported by LLM? derived from signal completeness? both?)

### 10.4 Explainability Generation `[LOCKED]`
Every scored lead returns structured explanation.

**Output structure [LOCKED]:**
- Bucket: HOT / WARM / COLD
- 5-dimension score breakdown: `fit 8/10, intent 9/10, engagement 6/10, behavioral X/10, context X/10`
- Key reasons (MAX 3): human-readable, specific
  - Example: "Requested pricing twice in 48 hours. Mentioned competitor. Industry match confirmed."
- Suggested action: "Call today. Lead is actively evaluating."
- Confidence: percentage

**Rule:** Salespeople won't act on black-box scores. Explainability drives adoption.

**Open:**
- `[TBD]` — Output JSON schema for LLM response (exact field structure)
- `[TBD]` — LLM output validation logic (what to do when LLM returns malformed JSON)
- `[TBD]` — Suggested action taxonomy (call, email, WhatsApp, nurture, hold, discard, escalate)

### 10.5 Lead Lineage Log `[LOCKED — critical infrastructure]`
Immutable audit trail. Non-negotiable.

**Logged per lead per agent step:**
- `agent_id, timestamp, tenant_id, lead_id`
- Input state snapshot (what the agent received)
- Output state (what the agent produced)
- Prompt version used (Agent D/E only)
- Confidence score at each step

**Build rule [LOCKED]:** Build lineage logging BEFORE adding the second agent, not after the eighth. Cost is low early, enormous when retrofitting.

**Open:**
- `[TBD]` — Lineage storage (same Postgres vs dedicated table vs object storage)
- `[TBD]` — Retention policy (days/months)
- `[TBD]` — Log field-level schema

### 10.6 Output of Phase 05
- Scored, bucketed, explained lead record
- All 5 dimension scores stored
- Explanation stored as human-readable string
- Full lineage written
- Status: `enriched`

### Open tickets for Phase 05
- LLM provider + model selection (biggest cost decision)
- Disqualification rule set
- Confidence calculation methodology
- Output JSON schema
- Output validation layer
- Lineage log schema + retention
- Human review queue design

---

## 11 — Phase 06: Output, SLA, Decay, Feedback v1

### 11.1 Bucket Definitions `[LOCKED]`

**HOT (75-100)** — Act within 24 hours
- Requested pricing or demo
- Multiple touchpoints in short window
- Mentioned competitor or urgency
- Returning buyer with past purchase history

**WARM (45-74)** — Nurture this week
- Engaged but no price/demo request yet
- Good fit, intent signals moderate
- Responded to content, not transactional yet
- First-time inquirer with solid profile

**COLD (0-44)** — Low priority, monitor passively
- Sparse data, low confidence
- No intent signals present
- Out of service area or irrelevant industry
- No response after initial contact

### 11.2 Action SLA Framework `[LOCKED — Add-on 4c]`
Buckets tie to enforceable SLAs:

| Bucket | Action SLA |
|---|---|
| HOT | Contact within 24 hours |
| WARM | 2-3 days |
| COLD | Weekly nurture |

**Rule:** Stale HOT lead (SLA breach) triggers automated alert to team lead.

**Open:**
- `[TBD]` — SLA alert delivery mechanism (chat message? email? both?)
- `[TBD]` — Whether SLAs are per-tenant configurable

### 11.3 Score Decay Job `[LOCKED — Add-on 4b]`
Background job prevents stale scores.

**Decay rules [LOCKED]:**
- No activity for 7 days → score -10
- No response for 14 days → score -20
- Dormant >30 days → auto-move to cold

**Open:**
- `[TBD]` — Decay job schedule (hourly? daily?)
- `[TBD]` — Whether decay rules differ per tenant

### 11.4 Chat Interface Output `[LOCKED format]`
Output format in chat:
- Summary: "Enriched 12 leads. 3 hot, 6 warm, 3 cold."
- Hot leads listed first with name, score, and one-line reason
- Suggested action per lead (call, WhatsApp, email, hold)
- Flagged leads (human review) listed separately
- Option to drill into any lead for full breakdown

### 11.5 Observability Logging `[LOCKED]`
Per pipeline run:
- Total runtime, per-agent duration
- Leads processed, enriched, flagged, failed
- Source success/failure rates
- API quota consumed per tenant
- Confidence distribution across output leads

**Rule:** Build observability BEFORE adding second agent.

**Open:**
- `[TBD]` — Observability tooling (Grafana? Datadog? custom?)
- `[TBD]` — Alerting thresholds

### 11.6 Feedback Loop v1 `[LOCKED — v1 only, v2 deferred to Add-on 6]`
**v1 (this scope):**
- Salesperson marks outcome: converted / not converted / wrong bucket
- Reason tags: wrong timing, wrong contact, wrong product, budget
- Outcomes aggregated weekly per tenant
- Scoring weight adjustments reviewed monthly (NOT automated initially)

**Edge case [LOCKED]:** Sales team doesn't fill feedback. Make it ONE TAP — thumbs up/down per lead card. If feedback rate drops below 20%, alert team lead. Zero feedback means zero learning.

**Deferred to v2 (Add-on 6):** Three-layer feedback architecture (weekly signal accuracy, monthly weights, quarterly signal vocabulary). See Section 17.

**Open:**
- `[TBD]` — Feedback UI (thumbs up/down + optional reason tags)
- `[TBD]` — Weekly aggregation report format

### Open tickets for Phase 06
- Bucket threshold calibration per tenant
- SLA alerting mechanism
- Decay job implementation
- Observability tooling selection
- Feedback UI design

---

## 12 — Phase 07: State Store, Registry, Build Order

### 12.1 Capability Registry Pattern `[LOCKED]`
Registry maps use case → ordered list of agent IDs.

**Example mappings:**
- `lead_enrichment` → `[source_fetch, gather, normalise, prompt_build, enrich]`
- Future `social_growth` → `[platform_audit, content_analyse, benchmark, recommend]`

**Rule:** Adding new use case = (1) build new agents, (2) test in isolation, (3) add one line to registry config. Orchestrator requires ZERO changes.

**Anti-pattern (from chat) `[LOCKED]`:** Do NOT build "auto-generate subagents" capability. That's not production-ready. Correct approach is registry of pre-built, tested agents.

**Open:**
- `[TBD]` — Registry storage format (YAML? JSON? DB table?)
- `[TBD]` — Registry versioning

### 12.2 State Store Design `[LOCKED — Postgres only initially]`
**Rule:** Start with Postgres. No Kafka, Redis Streams, or message queues at current scale. Those become relevant at thousands of leads per hour, not dozens.

**Core tables (field-level schemas are `[TBD]` per table ticket):**

| Table | Purpose | Status |
|---|---|---|
| `leads` | Lead identity + enrichment data + status | `[LOCKED existence, TBD fields]` |
| `pipeline_log` | Per-step lineage | `[LOCKED existence, TBD fields]` |
| `tenant_config` | Operational settings per tenant | `[LOCKED existence, TBD fields]` |
| `personas` **NEW** | Rich business persona per tenant | `[LOCKED existence, see Section 15]` |
| `prompt_registry` | Versioned prompt templates | `[LOCKED existence, TBD fields]` |
| `feedback_events` | User verdicts and outcomes | `[LOCKED existence, TBD fields]` |
| `signal_definitions` **NEW** | Foundation for deferred Add-on 7 | `[LOCKED existence, deferred population]` |
| `dry_run` | Dry run mode outputs | `[TBD]` |
| `human_review_queue` | Leads awaiting review | `[TBD]` |

**Tables NOT in v2.0 (deferred):**
- `signal_lineage` (Add-on 7)
- `signal_integrity_metrics` (Add-on 7)

### 12.3 Build Order `[LOCKED — revised for v2.0]`
Serial construction. Each layer validates the one beneath. Every sprint ends deployable.

1. Lead schema + state store (Postgres tables)
2. **Personas table (NEW in v2.0)**
3. Orchestrator skeleton with mock agent responses
4. Agent A (one source only — website first)
5. Agent C (normaliser) — validates Agent A output
6. Observability logging layer
7. Agent E (enrichment) — first end-to-end test
8. Agent B (gather), Agent D (prompt build)
9. **Disqualification + Decay + SLA rules (NEW in v2.0)**
10. Feedback loop v1
11. Add WhatsApp and Instagram to Agent A
12. Multi-tenant config layer expansion

**Rule:** Building all agents simultaneously means five things that work in isolation and nothing that works together.

### Open tickets for Phase 07
- Per-table schema definition (one ticket per table)
- Registry implementation
- Build order sprint planning

---

## 13 — Data Model Reference

### 13.1 Tables inventory
See Section 12.2 for table list and status.

### 13.2 Field-level schemas `[TBD for all — one ticket per table]`
Deliberately not filled. Each table schema will be decided in its own ticket to avoid premature locking.

**Known fields from chat (not schemas, just mentions):**

**`leads` table — fields mentioned in chat:**
- `lead_id`, `tenant_id`, `pipeline_stage`, `enrichment_data` (JSON), `confidence`, `status`, `created_at`, `updated_at`

**`pipeline_log` table — fields mentioned in chat:**
- `run_id`, `lead_id`, `agent_id`, `input_snapshot`, `output_snapshot`, `duration_ms`, `error`

**`tenant_config` table — fields mentioned in chat:**
- `tenant_id`, `scoring_weights`, `active_channels`, `thresholds`

### 13.3 Schema design principles `[LOCKED]`
- Every record MUST have `tenant_id` (multi-tenant from day 1)
- JSON columns acceptable for enrichment_data (flexibility)
- Timestamps in UTC ISO 8601
- Soft deletes preferred over hard deletes (audit trail)

### Open tickets for data model
- One ticket per table for field-level schema
- Indexing strategy
- Migration strategy
- Partitioning strategy (if needed at scale)

---

## 14 — Agent vs Tool Classification Matrix

### 14.1 Full matrix `[LOCKED]`

| # | Component | Type | Reasoning |
|---|---|---|---|
| 1 | Orchestrator | TOOL | Deterministic workflow engine |
| 2 | Intent Classification | TOOL | Rule/small-model mapping |
| 3 | Tenant Config Load | TOOL | DB fetch |
| 4 | Persona Load | TOOL | DB fetch |
| 5 | Confirmation UX | TOOL | Templated message |
| 6 | Agent A — Source Fetch | TOOL | API calls + parsing |
| 7 | Rate Limiter | TOOL | Quota checks |
| 8 | Deduplicator | TOOL | Matching algorithm |
| 9 | Agent B — Internal Lookup | TOOL | DB queries |
| 10 | Agent B — Public Verification | TOOL | Permitted API calls |
| 11 | Signal Collection | TOOL | Structured extraction |
| 12 | Agent C — Normaliser | TOOL | Schema transformation |
| 13 | Conflict Resolver | TOOL | Rule-based |
| 14 | Agent D — Prompt Builder | TOOL | Template assembly |
| 15 | **Agent E — LLM Scorer** | **LLM AGENT** | **Holistic judgment** |
| 16 | Output Validator | TOOL | Schema check |
| 17 | Disqualification Gate | TOOL | Rule-based |
| 18 | Bucketing | TOOL | Threshold comparison |
| 19 | SLA Tracker | TOOL | Time-based alerts |
| 20 | Decay Job | TOOL | Scheduled job |
| 21 | Feedback Collector | TOOL | Event ingestion |
| 22 | Observability Logger | TOOL | Metrics emission |

**Total: 1 LLM AGENT, 21 TOOLS**

### 14.2 Cost + reliability implications `[LOCKED reasoning]`
- LLM calls are expensive + variable + slow
- Rules are cheap + consistent + fast
- Minimizing LLM calls to 1 per lead keeps system affordable at scale

**Open:**
- `[RESEARCH NEEDED]` — Per-lead cost estimate at chosen LLM provider

---

## 15 — Persona Schema Deep-Dive [Add-on 2]

### 15.1 Why persona is a first-class entity `[LOCKED]`
Generic scoring fails because Urvee B2C organic buyers have nothing in common with Gamoft B2B IT prospects. Same incoming signal ("visited pricing page") means different things per tenant. Persona is what makes the LLM's judgment tenant-aware.

### 15.2 Persona schema (from chat) `[LOCKED fields, TBD values]`

```json
{
  "tenant_id": "gamoft_001",
  "business_type": "B2B | B2C | Hybrid",
  "industry": "string",
  "target_roles": ["CTO", "Director", "Procurement Head"],
  "company_size_preference": ["SME", "Enterprise"],
  "geography_focus": ["India", "EU"],
  "sales_cycle": "Short | Medium | Long",
  "ticket_size": "Low | Medium | High",
  "decision_complexity": "Single | Multi-stakeholder",
  "priority_signals": ["intent", "authority", "budget"],
  "negative_signals": ["student", "job seeker"]
}
```

### 15.3 Per-tenant persona — current state `[TBD for all]`

**Urvee Organics:**
- `[LOCKED]` business_type: B2C
- `[TBD]` full persona — requires tenant input

**Gamoft:**
- `[LOCKED]` business_type: B2B
- `[TBD]` full persona — we are the tenant, should be easiest

**Govmen:**
- `[TBD]` everything — chat has minimal info about this tenant

### 15.4 How persona integrates
- **Phase 00:** Loaded with tenant config
- **Phase 04:** Injected into prompt
- **Phase 05:** LLM evaluates lead against persona
- **Phase 06:** `priority_signals` and `negative_signals` influence bucketing nuance

### Open tickets for persona
- One persona-definition ticket per tenant (requires tenant interviews)
- Persona versioning strategy
- Persona update workflow (when tenant business changes)
- Persona validation (prevent nonsensical combinations)

---

## 16 — Open Decisions / TBD Registry

Master index of every `[TBD]` in this document. Use this to prioritize ticket creation.

### 16.1 Technology stack `[TBD — high priority]`
- Backend language/framework `[TBD — Laravel (Anishekh's memory) vs Python vs Node]`
- LLM provider `[RESEARCH NEEDED — OpenAI/Anthropic/Groq/NVIDIA NIM]`
- LLM model selection per tenant
- Database (Postgres `[LOCKED]`) — version, hosting
- Secrets vault
- Observability tooling
- Hosting `[ASSUMPTION CHECK — AWS from memory]`

### 16.2 Per-tenant decisions `[TBD]`
- Urvee full persona
- Gamoft full persona
- Govmen full profile + persona
- Tenant-specific scoring weight starting values
- Tenant-specific disqualification rules
- Tenant-specific prompt templates

### 16.3 Schema decisions `[TBD — one ticket per table]`
- `leads` table fields
- `pipeline_log` fields
- `tenant_config` fields
- `personas` fields
- `prompt_registry` fields
- `feedback_events` fields
- `signal_definitions` fields (placeholder for deferred)
- `dry_run` fields
- `human_review_queue` fields
- Indexing strategy
- Retention policies

### 16.4 Algorithm decisions `[TBD]`
- Intent classifier (rule/model)
- Deduplication matching threshold
- Confidence calculation method
- Output JSON validation rules
- SLA alert timings

### 16.5 UX decisions `[TBD]`
- Confirmation message wording
- Lead card display format
- Feedback UI (thumbs + reasons)
- Human review queue surface
- Drill-down format
- Alert delivery mechanism

### 16.6 Operational decisions `[TBD]`
- Rate limit quotas per API per tenant
- Decay job schedule
- Observability alert thresholds
- Dry run tooling
- Deployment strategy
- Testing strategy

### 16.7 Compliance `[RESEARCH NEEDED]`
- LinkedIn API access strategy
- Instagram Business Discovery scope
- WhatsApp Business API permissions
- Data retention per jurisdiction
- Tenant data isolation audit

### 16.8 Team + Timeline `[TEAM INPUT]`
- Team size on this project
- Sprint duration
- MVP deadline
- Review process

---

## 17 — Deferred Add-ons (6, 7, 8) — Full Reference

**Status: `[DEFERRED]` to Sprint 2-3. Not in v2.0 scope. Kept here for future ticket discussions.**

### 17.1 Why deferred `[LOCKED reasoning]`
- Shadow mode needs real leads to shadow
- Integrity scoring needs real conversion outcomes
- Auto-discovery needs real mis-bucketed patterns
- Without 2-3 months of production data, these systems measure nothing and discover nothing
- Building on hypothetical data produces expensive random number generators

### 17.2 Add-on 6 — Three-Layer Feedback Architecture `[DEFERRED]`
Replaces the single weights-only feedback loop with three loops on different clocks:

**Layer 1 (monthly):** Weights tuning — existing in v1
**Layer 2 (weekly):** Signal extraction accuracy via reason-tagged feedback
**Layer 3 (quarterly):** Signal vocabulary evolution

All feed from the same lineage log.

### 17.3 Add-on 7 — Adaptive Signal Lifecycle `[DEFERRED]`
The unified subsystem combining three mechanisms:

**(a) Trust Mechanism — Integrity Scoring**
Four pillars evaluated continuously:
- **Lift** (40%): conversion rate with signal / baseline — threshold ≥1.3x
- **Sample confidence** (25%): minimum 50 leads, confidence interval check
- **Stability** (25%): rolling 4-week lift trend — 2 consecutive weeks below 1.0x triggers auto-deprecation
- **Independence** (10%): co-occurrence with other signals <80%

Plus extraction integrity audit: biweekly LLM verifies 20 random leads where signal fired. <85% accuracy → `under_review`.

Aggregate `integrity_score` (0-100) per signal. Lifecycle states driven automatically:
```
shadow → candidate → active → under_review → deprecated
```

Only `candidate → active` requires human approval.

**(b) Discovery Mechanism**
Biweekly background job:
1. Examines mis-bucketed leads (predicted vs actual outcomes)
2. Passes raw data through LLM with prompt: "What patterns do these leads share that our current signals miss?"
3. LLM proposes candidate new signals
4. Inserted at `shadow` state in signal_definitions
5. Trust Mechanism evaluates them naturally over time

**Critical rule:** LLM suggests, human approves. Never auto-promote.

**(c) Feedback Mechanism (reason-tagged signals)**
Every user-visible "reason" string carries hidden `signal_id` linking back to source agent + prompt version.

When user taps "this reason was wrong":
- Orchestrator silently routes to per-signal accuracy dashboard
- Per-signal accuracy feeds Trust Mechanism
- User never sees signals, schemas, or agents

### 17.4 Add-on 8 — Business-Language User Confirmation `[DEFERRED]`
Single user touchpoint for entire Signal Lifecycle.

When Trust Mechanism flags a meaningful change (new signal ready for promotion, old signal failing), orchestrator asks ONE conversational question in chat:

> "Pichle 2 mahine mein noticed ki jo customers 'family health' mention karte hain woh 3x zyada convert ho rahe hain. Kya main aage se ye pattern consider karoon?"

Options: "Haan" / "Nahi" / "Aur data dikhao"

No Signal Studio UI. No technical surface. User never learns what a signal is.

### 17.5 Tables needed when 6-7-8 are built `[DEFERRED schemas]`
- `signal_lineage` — per-lead signal extractions with `signal_id` mapping
- `signal_integrity_metrics` — calculated lift/stability/independence per signal per tenant
- `signal_feedback_events` — reason-level verdicts linked to signal_ids
- Extensions to `signal_definitions` — status, metrics, audit dates

### 17.6 Why combine these three into ONE subsystem `[LOCKED reasoning]`
Chat stress-tested this: all three (reason-tagging, auto-discovery, integrity scoring) share:
- Same data infrastructure (signal_lineage, signal_definitions)
- Same user-facing surface (business-language confirmation)
- Same purpose (evolving the signal vocabulary)

Separating them would force duplicate jobs, duplicate tables, inconsistent state. They form ONE subsystem: "Adaptive Signal Lifecycle."

### 17.7 Prerequisite: Phase 1 data collection
Before building 6-7-8, Phase 1 must have produced:
- `[TBD]` — number of leads per tenant needed
- `[TBD]` — minimum months of feedback data
- `[TBD]` — baseline conversion rates established

---

## 18 — Glossary

### Core terms
- **Agent** — Component using LLM for judgment-based output
- **Tool** — Component executing deterministic logic
- **Orchestrator** — Central controller; only thing user interacts with
- **Tenant** — A client organization (Urvee / Gamoft / Govmen)
- **Persona** — Rich business profile per tenant (Add-on 2)
- **Lineage Log** — Immutable audit trail of every transformation
- **Bucket** — HOT / WARM / COLD classification
- **Confidence** — System's trust in its own score (0-100%)
- **Signal** — Structured observation about a lead (e.g., `pricing_intent: high`)
- **Dry Run** — Full pipeline execution with no production side effects
- **Shadow Mode** — (Deferred) Signal extracted but not used in scoring

### Agent names reference
- **Agent A** — Source Fetch
- **Agent B** — Data Gather
- **Agent C** — Normalise
- **Agent D** — Prompt Construction
- **Agent E** — LLM Scoring (the only true LLM agent)

### Key acronyms
- **SLA** — Service Level Agreement (action timelines per bucket)
- **E.164** — International phone number format (+91XXXXXXXXXX)
- **ICP** — Ideal Customer Profile
- **AOV** — Average Order Value
- **CLV** — Customer Lifetime Value
- **B2B** — Business-to-Business
- **B2C** — Business-to-Consumer

---

## 19 — Key Decisions: Verbatim Reasoning from Chat

This section preserves the original chat reasoning for the most important architectural decisions. Use when a ticket questions a decision and you need to recall why it was made.

### 19.1 Why only 1 LLM agent, not 20+
From chat analysis of manager's proposal: *"Most teams make mistake of either too few agents (monolithic) or too many (orchestration chaos)."*

Decision: Functional clustering, but classify each component as LLM_AGENT or TOOL. LLM = Thinking, Tools = Doing, Orchestrator = Controlling. Only use LLM where judgment/ambiguity/personalization matters. Everything else = tools. Cost + reliability both fix.

### 19.2 Why persona layer over simple tenant_config
From stress-test: *"Same lead → different score across tenants is by design."* Urvee B2C organic buyer and Gamoft B2B IT prospect have nothing in common. A director-level lead for small company: for Gamoft scores 55 (warm), for Urvee scores 30 (cold). Without persona layer, system is generic CRM. This is the competitive moat.

### 19.3 Why feedback loop must be three-layer (deferred)
Original feedback loop attached to wrong layer. Adjusting weights fixes nothing when the real error is upstream:
- Bad signal extraction (Agent B)
- Bad enrichment (wrong LinkedIn profile)
- Bad normalisation
- Bad prompt template
- Bad LLM judgment
- Only THEN bad weights

Treating symptom not disease. Three layers fix three different failure modes at three different cadences.

### 19.4 Why user never sees signals
Tension: feedback loop needs signal-level diagnostic data, but user only speaks in outcomes. Resolution: reason-tagged signals. User sees "Requested pricing twice" (human language). System maps that to `signal_id` internally. User grades reasons; system hears signal-level feedback. **"The user interface and the diagnostic interface are not the same interface."**

### 19.5 Why adaptive layer deferred
*"Shadow mode needs real leads to shadow. Integrity scoring needs real conversion outcomes. Building on hypothetical data produces expensive random number generators."* Ship v2.0, collect 2-3 months of data, then build adaptive layer on actual patterns.

### 19.6 Why Postgres-only, no Kafka
*"Start with Postgres. You do not need Kafka, Redis Streams, or a message queue at your current scale. Those become relevant at thousands of leads per hour, not dozens."* Don't pre-optimize infra for scale you don't have.

### 19.7 Why prompts are code
Prompt quality drops silently. Must know which prompt version produced which score. Version control, review, rollback same as code. Every agent call logs prompt version.

### 19.8 Why lineage log is non-negotiable
*"Without observability, you cannot know which agent is slow, which source is failing, or whether scoring quality is drifting. Observability turns a working prototype into a maintainable production system."* Cost is low when system is small. Cost of retrofitting with 8 agents is enormous.

### 19.9 Why confidence is first-class, not just routing
Two leads scoring 85 needing different actions based on confidence. Score without confidence is overconfident and destroys sales team trust faster than honest uncertainty. Making it user-visible is the differentiator.

### 19.10 Why no "Agent Builder" agent
Manager's ChatGPT kept suggesting dynamic agent creation. Chat rejected: *"That's not production-ready. The correct approach is a registry of pre-built, tested agents."* Auto-generating subagents is anti-pattern. Registry + manual additions = scalable.

---

## 20 — Hinglish Quick-Reference

### Core principles in Hinglish
- **User ko agents ka pata nahi chalega.** Woh sirf chat mein baat karta hai. Signals, schemas, agents — sab hidden.
- **LLM sirf judgment ke liye.** Baaki sab deterministic. Ek hi LLM agent pipeline mein — Agent E.
- **Persona sabse important.** Urvee, Gamoft, Govmen — sabke alag personas. Same lead, different score across tenants. Yahi moat hai.
- **Confidence aur score dono dikhenge.** 85 score + 90% confidence ≠ 85 score + 40% confidence.
- **Lineage log hamesha.** Doosre agent se pehle ye build karna hai. Baad mein retrofit karna mehenga hoga.

### Build order in Hinglish
1. Schema + state store pehle
2. Personas table (NEW)
3. Orchestrator skeleton
4. Agent A (sirf website)
5. Agent C (validate A)
6. Observability layer — critical, dusre agent se pehle
7. Agent E end-to-end test
8. Agent B + D
9. Disqualification + decay + SLA (NEW)
10. Feedback v1
11. WhatsApp + Instagram add karo
12. Multi-tenant expand

### Add-ons in Hinglish
1. **Agent vs Tool tag** — har component pe label
2. **Persona layer** — tenant ka rich business profile
3. **Confidence first-class field** — user ko dikhe
4. **Disqualify + Decay + SLA** — scoring ko execution mein convert karo
5. **State store schema** — sab Postgres, Kafka abhi mat lagao

### Deferred add-ons (Sprint 2-3)
6. **Three-layer feedback** — weekly/monthly/quarterly alag clocks
7. **Adaptive Signal Lifecycle** — signals khud discover + integrity check + shadow mode
8. **Business-language confirmation** — user ko ek sawaal, signal ka naam nahi

### Why defer 6-7-8
Data chahiye pehle. 2-3 mahine production data ke bina ye bekaar hain. Pehle v2.0 ship kar, fir real data pe adaptive layer banaa.

---

## Appendix A — Document Update Log

| Date | Update | By |
|---|---|---|
| 2026-04-14 | Initial compilation from chat | Anishekh + Claude |

**Future updates:** Add entry per ticket resolution. When `[TBD]` becomes decided, change to `[LOCKED]` and log here with ticket ID.

---

## Appendix B — How this document is used

1. **Claude terminal ingestion:** `ingest lead_intelligence_engine_reference.md` in VS Code Claude terminal
2. **Obsidian import:** Drop into vault root; backlinks will work across future ticket notes
3. **Ticket creation:** Every `[TBD]` becomes a JIRA ticket; reference this doc's section number in ticket description
4. **Ticket resolution:** When ticket closes, update this doc's relevant section: change `[TBD]` to `[LOCKED]`, document decision, add to Update Log
5. **After ~100 tickets:** Derive final PRD and technical spec documents from the fully resolved reference

---

## Appendix C — What This Document Is NOT

- **NOT a PRD** — no business justification, no stakeholder alignment, no approval signoff structure
- **NOT a technical spec** — field-level schemas deliberately unspecified until ticket discussions
- **NOT a design doc** — no UI mockups, no wireframes
- **NOT a project plan** — no dates, no resource allocation, no dependencies graph
- **NOT immutable** — every `[TBD]` is designed to be resolved through ticket discussions

This is pre-planning knowledge capture. Its purpose is to ensure no decision, context, or reasoning from the chat is lost before team discussions begin.

---

**End of document. File length: intentionally long for exhaustive reference. Navigate via section numbers.**
