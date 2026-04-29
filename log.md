# Wiki Log

*Append-only. Most recent entries at top.*

---

## [2026-04-30] analysis | Lead Enrichment + Investigation Architecture — Full Rewrite

- File rewritten: [[wiki/analyses/lead-enrichment-architecture]]
- File deleted: [[wiki/analyses/enrichment-provider-stack]] — merged in
- Triggered by: design conversation on lead investigation, scraper reliability, and India-specific provider stack

### What changed

**PDL on hold:** Poor coverage for Indian B2C (~20–30%) and B2B SMBs — not reliable enough for the primary pipeline.

**Two-phase enrichment model introduced:**
- Phase 1 (sync, before initial score): Tier 1 first-party + Tier 2 identity (Truecaller + Google Places)
- Phase 2 (async investigation, runs on every lead): deep social + business enrichment; score updates when complete

**India-specific investigation stack locked:**
- B2B: GST API (turnover slab — free, official), MCA API (company type/capital — free, official), JustDial (SMB profile), IndiaMART (trader/buyer status), Apollo.io (corporate employees only)
- B2C: Truecaller bio (lifestyle signals), Instagram Graph API (official), Apify Instagram (public posts only)
- Dropped: LinkedIn post scraping (too unreliable), Facebook profile scraping (mostly private, near-zero yield), WhatsApp investigation (closed system)

**Key insight:** Phone number is India's primary identity layer. Truecaller + GST + MCA give more reliable signal for Indian leads than any Western data provider. GST turnover slab directly answers B2B budget qualification.

**3 new B2B extractor types added:** gst_turnover_threshold, company_type_match, business_directory_presence (in addition to 3 existing B2C types)

**Cost model revised:** ~$180–270/mo at 300 leads/day (down from prior estimate due to free government APIs replacing paid providers)

### Open items carried forward
- 6 new extractor types not yet in signal-detection-rule-spec
- identity_graph and channel_connection entities not yet in data-entity-model
- lead_completeness formula not yet defined
- JustDial/IndiaMART: API vs scrape path not confirmed
- YouTube identity link practical path not confirmed

---

## [2026-04-28] analysis | Enrichment Provider Stack + Channel Integration Decisions

- File created: [[wiki/analyses/enrichment-provider-stack]]
- Triggered by: design conversation on exact tools, configuration, and day-1 enrichment coverage

### What was decided

**Provider stack locked:**
- Truecaller for Business — phone verification + India location coverage (~$0.001/call)
- People Data Labs (PDL) — phone/username → social handles + LinkedIn URL; pay-per-match only
- Apollo.io — LinkedIn URL → structured B2B data (job title, company, seniority)
- Instagram Graph API — IGSID/username → bio + profile (free, tenant Meta token)

**Internal identity graph as caching layer:**
- Checked before any external call; populated after every successful enrichment
- Day 1: every lead goes to external providers
- Over time: cache hit rate rises, external calls decrease
- Cannot replace external providers on day 1 — starts empty

**Why build-it-ourselves alone fails:**
- Internal identity graph starts empty; no enrichment coverage on first run
- SerpAPI search is a fallback, not a primary provider
- Real provider (PDL) needed from day 1

**Per-channel free data from webhook:**
- WhatsApp: phone + display name + message (display name avoids Truecaller name call)
- Instagram DM: IGSID → one Graph API call → username (Tier 3 enrichment starts here, free)
- Facebook DM: PSID → name only (thinnest enrichment path)
- LinkedIn Lead Ad: full profile included (skip all external calls)

**Non-text message types locked:** image (URL stored), audio (Whisper deferred), story reply (text + story ref — strong signal), product catalogue tap (product ID — highest intent signal), button click (label — strong intent)

**WhatsApp options locked:** Direct WABA (our Meta App) or BSP connector (Interakt/WATI/AiSensy) — adapter pattern, both produce identical NormalisedEvent

**Coverage expectations set:** PDL hits ~20–30% Indian B2C, ~40–55% B2B — expected behavior, not failure; low-coverage leads scored on message content + channel signals

**Cost model:** ~$270/mo at 300 leads/day; drops to ~$110/mo at 60% cache hit rate (Month 6+)

### Open items
- `identity_graph` entity not yet in data entity model — needs to be added
- Cache TTL for identity graph entries (topic_affinity especially can go stale)
- Instagram biography field availability for personal vs. creator accounts
- Whisper transcription for voice notes — deferred, flagged for post-MVP

---

## [2026-04-28] analysis | Lead Enrichment Architecture + Channel Integration Layer

- Files created: [[wiki/analyses/lead-enrichment-architecture]], [[wiki/analyses/channel-integration-layer]]
- Triggered by: design discussion on how enrichment works, how tenants connect platforms, and how Tier 3 social enrichment improves B2C scoring accuracy

### What was decided

**Signal separation principle (non-negotiable architectural rule):**
- Signals are created ONLY from ICP + tenant persona in Pipeline 2 — no lead data involved
- Enrichment is independently collected in Pipeline 1 — no signal awareness
- Signal evaluation is the bridge: detection_rules run against NormalisedEvent to produce 0.0–1.0 values
- These three steps are always distinct and must never be conflated

**Three-tier enrichment model:**
- Tier 1: first-party interaction data (message content, website behavior, lead history) — always available, $0
- Tier 2: identity resolution + firmographic (Truecaller for phone verify, Clay/PDL for social handle discovery, Apollo/Clearbit for B2B firmographic) — ~$0.005–$0.02/lead
- Tier 3: social behavioral enrichment (Instagram Graph API for public profile + posts, Apollo for LinkedIn topics) — ~$0.02–$0.10/lead, requires Tier 2 to have found a social handle

**Tier 3 step-by-step from name + phone:**
1. Truecaller → verified name, city, spam check
2. Clay/PDL identity graph → Instagram handle / LinkedIn URL (if indexed)
3a. Instagram Graph API → bio, recent post hashtags → topic_affinity inferred
3b. Apollo → LinkedIn job + posting topics
- Realistic Tier 3 success rate from WhatsApp: 15–25% (private accounts and no Meta phone registration = no Tier 3)

**Source channel affects enrichment difficulty:**
- Instagram DM / Facebook DM → social user ID in event payload → Tier 3 requires no lookup
- LinkedIn Lead Ad → full profile in form response → richest inbound source
- WhatsApp → phone only → all 3 steps required

**NormalisedEvent field expansion:** 6 new fields for Tier 2 identity handles + Tier 3 social behavioral data

**New extractor types required for B2C:** `topic_affinity_match`, `interest_category_match`, `bio_keyword_match` — must be added to signal-detection-rule-spec and Persona Agent Step 3 prompt

**New entity required:** `channel_connection` — not yet in data entity catalog; covers OAuth tokens, webhook endpoints, connection status per platform per tenant

**enrichment_tier_reached field** needed on `lead_enrichment` entity

### Files created
- [[wiki/analyses/lead-enrichment-architecture]] — enrichment tiers, Tier 3 flow, signal separation, NormalisedEvent expansion, new extractor types, B2C vs B2B strategy
- [[wiki/analyses/channel-integration-layer]] — OAuth flow per platform, channel_connection entity, webhook + polling event detection, payload normalisation adapters, token lifecycle

### Follow-up items flagged
- Add `channel_connection` to [[concepts/data-entity-model]] Group A
- Add `enrichment_tier_reached` field to `lead_enrichment` entity definition
- Add 3 new B2C extractor types to [[analyses/signal-detection-rule-spec]] and update Persona Agent Step 3 system prompt
- Confirm Clay.com vs PDL as primary Tier 2/3 provider
- Confirm Instagram Graph API scope for public post reading

---

## [2026-04-28] analysis | Signal Detection Rule — Format Specification

- File created: [[wiki/analyses/signal-detection-rule-spec]]
- Triggered by: design discussion on event trigger → lead enrichment flow; detection_rule was the last hard blocker
- Status: RESOLVES hard blocker flagged in 8 documents across the wiki

### What was decided
- **Format:** `{ type, source_fields, params }` — named extractor + params
- **Vocabulary:** 13 pre-built extractor types covering all 5 scoring dimensions (keyword_match, question_pattern, urgency_indicator, budget_authority_indicator, touchpoint_count, channel_diversity, recency_check, page_visit_match, form_completion_depth, source_type_match, utm_match, geography_match, company_attribute_match)
- **Output contract:** every extractor returns `(detected: bool, value: float 0.0–1.0, evidence: str)` — uniform across all types
- **No composition:** one extractor per signal; AND/OR logic is not supported; composition is handled by multiple signals across dimensions
- **Persona Agent change:** Step 3 now emits detection_rule JSON directly (not a placeholder). No engineering mapping step. Vocabulary table given in Step 3 system prompt.
- **Stateful extractors noted:** touchpoint_count, channel_diversity, recency_check require lead_history from DB — enrichment is not purely stateless
- **NormalisedEvent schema defined:** minimal schema all event sources normalize into before Pipeline 1 runs

### Files updated (blocker resolved in all)
- [[wiki/analyses/persona-agent-spec]] — Step 3 logic + output schema + open decisions
- [[wiki/analyses/orchestration-layer-spec]] — signal schema section + enrichment step + two open decisions table entries
- [[wiki/analyses/execution-type-classification]] — Open Question 3 + Follow-up 3
- [[wiki/analyses/tech-stack-research]] — Open Items #1 + Follow-up #5
- [[wiki/analyses/service-scaling-strategy]] — Caveats section
- [[wiki/concepts/data-entity-model]] — Open Questions (signal schema)
- [[wiki/overview]] — Open Question #1, What's TBD, What to Read Next, #12
- [[index]] — new analysis entry added

---

## [2026-04-26] analysis | Technology Stack Research — Complete Production Stack

- File created: [[wiki/analyses/tech-stack-research]]
- Triggered by: team request to research all tools for production microservices build
- Context established: AWS confirmed, EC2 account available, web chat on product site, signal detection_rule still TBD, senior dev decision = Microservices (not Monolithic)

### Locked decisions (no further discussion needed)
- Backend: Python 3.12 + FastAPI + Uvicorn + uv
- LLM: Anthropic Claude Sonnet 4.6 (primary) + OpenAI GPT-4o (fallback) via LiteLLM
- Containers: AWS ECS Fargate
- Auth: Clerk (native multi-tenancy, free tier, 4-role RBAC)
- Secrets: AWS Secrets Manager
- Observability: CloudWatch (MVP) → Grafana Cloud + Prometheus (Month 3+)
- Package manager: uv
- Ruled out: Laravel/PHP (no LLM ecosystem), Go (SDK friction), EKS (overkill), Lambda (15-min timeout), Datadog (cost), Auth0 (cost), Groq (no prompt caching), Vault (overkill), CockroachDB (overkill), Neon/Supabase (not AWS-native)

### Three open decisions (pending team discussion)
1. **Orchestration:** Temporal self-hosted on EC2 (~$30/mo, native crash recovery) vs AWS Step Functions (~$0.05/mo, no mid-task resumption) — full landscape of 14 tools researched; Celery/Airflow/Prefect/Dagster all ruled out
2. **Real-time chat:** Pusher + Beams (~$49/mo, zero ops) vs Soketi on EC2 + FCM (~$35/mo, Pusher-compatible, same code) — full landscape of 13 tools researched
3. **Database:** Aurora Serverless v2 (~$94/mo, zero ops, auto-scale) vs PostgreSQL on EC2 (~$42/mo, team owns ops) — full landscape of 10 options researched

### Budget scenarios documented
- Scenario A (Managed): ~$357/month excl. LLM tokens
- Scenario B (Hybrid self-hosted): ~$288/month excl. LLM tokens
- LLM cost (steady state with prompt caching): ~$27/month for 300 leads/day

---

## [2026-04-26] analysis | Agent Specifications — Persona Agent, Rating Agent, Future Optional Agents

- Files created: [[wiki/analyses/persona-agent-spec]], [[wiki/analyses/rating-agent-spec]], [[wiki/analyses/future-optional-agents]]
- Sources consulted: [[concepts/agent-vs-tool-classification]], [[concepts/intelligence-layer]], [[concepts/persona-layer]], [[concepts/signal-types]], [[analyses/orchestration-layer-spec]], [[analyses/execution-type-classification]], [[analyses/delivery-integration-layer]], [[analyses/scoring-quality-metrics]], [[concepts/confidence-first-class]]

### Persona Agent (persona-agent-spec.md)
- Defined as the Pipeline 2 configuration agent — 3 sequential LLM sub-agents (Business Persona → ICP → Signal Definitions)
- Inputs: tenant business description (from P2-1 intake), optional re-run context (feedback pattern, check-in change description), team_lead_approval required for re-runs
- Outputs: PersonaObject (scoring_weights, banding, custom_rules, tone), IcpDefinition (target_segment, priority_signals, disqualifying_signals, buying_triggers), signal[] (all 5 dimensions), prompt template (orchestrator generates post-Step-3, AUTOMATION)
- Named distinction from Persona Engine (TOOL that loads/caches at scoring time) explicitly documented
- Invocation: new tenant onboarding OR feedback-driven re-run OR check-in-driven re-run; never per-lead; never automatic
- Step 3 output constrained: weights_within_dim must sum to 1.0 per dimension

### Rating Agent (rating-agent-spec.md)
- Defined as the full score_lead() call — encompasses 4 internal components (Persona Engine, Prompt Layer, Rating Agent component, Output Schema Layer)
- Inputs: EnrichedLead, tenant_id, variant (new/returning/rescore), signal_values dict, prompt_template_version
- Score output: score (int 0-100), bucket (enforced by banding), sub_scores (per dimension)
- Reasoning output: reasoning (one-line), recommended_action (simple string — deliberately limited at MVP)
- Completeness output: lead_completeness (float 0.0-1.0) + needs_review (bool) — **NOT LLM confidence** (2026-04-22 correction maintained)
- Per-tenant concurrency cap: recommend 2 per tenant (not global) — prevents noisy neighbor
- Timeouts: 30s LLM call, 60s full score_lead(), 90s orchestrator budget
- Soft blocker noted: sub_scores has 4 fields in S2 spec vs 5 scoring dimensions — S2 to clarify

### Future Optional Agents (future-optional-agents.md)
- **Recommendation Agent:** fills gap between "what to do" and "how to approach this specific lead"; outputs personalized outreach draft, talking points, channel recommendation, timing window; unlock conditions: 3+ months data, AP1/AR2/AR3 stable, CRM outcomes connected; introduce as A/B opt-in for one tenant first
- **Workflow Agent:** adds judgment to lifecycle decisions (vs deterministic SLA/decay rules); outputs decision (rescore/escalate/hold_decay/archive), rationale, approval proposal; unlock conditions: 3+ months stability, AR1 baseline, tenant workflow patterns documented; introduce with narrow scope (re-score triggers only) first
- Both agents defined as enhancements, not corrections — MVP delivers full core value without them
- Defined what should NOT become an agent (deduplication, signal extraction, bucket enforcement, quality metrics)
- Principles for future agent expansion: data prerequisite, determinism, cost proportionality, oversight, minimal set tests

---

## [2026-04-26] analysis | Execution Type Classification — Automation / Agent / Hybrid

- Wiki page: [[wiki/analyses/execution-type-classification]]
- Question: Which steps in the Lead Intelligence Engine workflow are automation, agent-driven, or hybrid?
- Sources consulted: [[concepts/agent-vs-tool-classification]], [[analyses/orchestration-layer-spec]], [[concepts/intelligence-layer]], [[concepts/lead-pipeline-architecture]], [[analyses/governance-observability-layer]]

### Classification summary

- **AGENT (3 steps):** Onboarding Agent (P2-2), ICP Agent (P2-3), Signal Agent (P2-4) — all in Pipeline 2, all one-time per tenant
- **HYBRID (3 steps):** Tenant Info Intake (P2-1) — form scaffold + LLM strengthening of inputs; Scoring (P1-5) — Rating Agent LLM call + Output Schema Layer banding enforcement; Proactive Check-In (G-10) — conditional on classifier type (TBD)
- **AUTOMATION:** All remaining steps — Data Gather, Lead Enrichment (both phases), Normalise, Prompt Fill, Disqualification Gate, Bucketize, routing, delivery, all lineage/governance/background jobs

### Key architectural findings

- The hybrid boundary at Scoring (P1-5) is defined by the Output Schema Layer enforcing banding rules that can override the LLM's bucket — within the same atomic `score_lead()` call. This is not a separate validation step.
- Signal extraction (P1-2b) is AUTOMATION despite using signal definitions created by an LLM Agent (P2-4). Intelligence is front-loaded into signal design; execution is deterministic per-lead.
- The 1-LLM-call-per-lead guarantee holds: the only per-lead LLM cost is in the HYBRID Scoring step (Rating Agent component).
- Three open questions can shift G-9, G-10 classifications: check-in classifier type, recommendation wording approach, detection_rule format.

### Design implications documented

- Test strategy per execution type (unit tests for AUTOMATION, eval suites for AGENT, both for HYBRID)
- Debugging approach: check signal extraction values first, then LLM judgment
- Cost attribution: LLM costs incurred only in AGENT and HYBRID steps
- Observability signal scope per execution type

---

## [2026-04-26] schema-update | Flag deleted analyses — success-metrics-framework and success-metrics-brief

- Files affected: index.md
- success-metrics-framework.md: marked DELETED in index; file was removed from filesystem; log entries from 2026-04-14 and 2026-04-16/17 preserved; content superseded by scoring-quality-metrics combined doc
- success-metrics-brief.md: marked DELETED in index; file was removed from filesystem; log entries from 2026-04-17 preserved

---

## [2026-04-24] analysis | Service Scaling Strategy — Three MVP Services

- Question: What are the best ways to scale the Ingestion, Orchestration+LLM, and Reporting services?
- Wiki page: [[wiki/analyses/service-scaling-strategy]]
- Reference: Tod Golding, *Building Multi-Tenant SaaS Architecture* (O'Reilly)
- Sources consulted: orchestration-layer-spec, delivery-integration-layer, governance-observability-layer, concepts/intelligence-layer, concepts/lead-pipeline-architecture, scoring-quality-metrics

### Key findings

- **Isolation model:** Pool for all three services at MVP. ~300 leads/day across 3 tenants does not justify silo infrastructure. Bridge model is the long-term commercial direction.
- **#1 architectural win:** Change Scoring Agent concurrency cap from global (5) to per-tenant (2 per tenant). Current global cap allows one tenant's batch to starve all others — textbook noisy neighbor. Per-tenant semaphore keyed on tenant_id fixes this in ~20 lines of code.
- **Ingestion:** Job queue absorbs spikes; every job stamped with tenant_id at intake; per-tenant rate limits per channel connector; lineage writes are non-negotiable (must not be batched or delayed); idempotent enrichment required before retry logic added.
- **Orchestration+LLM:** Per-tenant concurrency cap; per-tenant LLM config stored in tenant record; system message used for prompt caching; 60s hard timeout enforced; crash recovery via pipeline_stage already locked in design.
- **Reporting:** quality_snapshots is the enforced read model — no dashboard query touches raw pipeline tables; read replica connection string separated from day one; RBAC enforced server-side in API layer; scheduled reports pre-computed by background job; per-tenant LLM cost metering logged at call time.
- **Tiering framework:** Basic/Standard/Premium config schema designed now, activated later. Per-tenant config fields for concurrency cap, token budget, API rate limit, report schedule.
- **Five changes that move the needle now:** (1) per-tenant concurrency cap, (2) per-tenant config schema with limit fields, (3) tenant_id stamped at queue intake, (4) quality_snapshots rule enforced, (5) LLM token usage logged per tenant per call.

### Constraints verified

- All 15 recommendations cross-checked against locked design decisions. No conflicts with: 1 LLM call per lead, governance failure must not halt pipelines, delivery failures never roll back Pipeline 1, system proposes / human approves, lineage write-order rule, pipeline_stage crash safety guarantee, RLS + JWT + RBAC.

---

## [2026-04-22] schema-update | Cross-document propagation — Delivery and Integration Layer

- Trigger: delivery-integration-layer.md created; all other docs updated to reference it and reflect its position in the system architecture

### Files updated

**wiki/analyses/orchestration-layer-spec.md**
- Section 2 (main architecture diagram): "Bucketize → salesperson" → "Bucketize"; added DELIVERY AND INTEGRATION LAYER box between Pipeline 1 output and GOVERNANCE LAYER; shows feedback signal flow back to governance
- Section 4.2 (Pipeline 1 stage flow): Bucketize bottom replaced with DELIVERY AND INTEGRATION LAYER box instead of "Salesperson sees ranked lead cards in chat"
- Section 4.2 (Bucketize box): "confidence routing" corrected to "completeness routing"
- Section 6.3 step 10: updated to reference Delivery Layer handoff and [[analyses/delivery-integration-layer]]

**wiki/analyses/governance-observability-layer.md**
- Section 1 (position diagram): redesigned to show Pipeline 1 output first going to Delivery Layer, then feedback signals flowing from Delivery Layer to Governance Layer
- Section 2.3 (alert delivery): added reference to [[analyses/delivery-integration-layer]] Section 4 (notification_delivery entity, channel decisions)
- Section 5.5 (team lead notification delivery): added reference to [[analyses/delivery-integration-layer]] Section 4

**wiki/overview.md**
- Current Thesis: added paragraph on Delivery Layer (what it covers, delivery failures never roll back Pipeline 1, full spec reference)
- Major Themes: added delivery-integration-layer analysis entry
- Key Analyses table: added delivery-integration-layer.md as COMPLETE 2026-04-22; fixed confidence-scoring-brainstorm from "IN PROGRESS" → "RESOLVED 2026-04-22"; corrected orchestration-layer-dependencies to SUPERSEDED

**wiki/concepts/data-entity-model.md**
- Related Concepts: added [[analyses/delivery-integration-layer]] entry for Group C delivery entities

**wiki/concepts/lead-pipeline-architecture.md**
- Pipeline diagram: added DELIVERY AND INTEGRATION LAYER between Bucketize and GOVERNANCE LAYER with feedback signal flow
- Pipeline 1 stage table: Scoring Agent output corrected (confidence → lead_completeness, needs_review)
- Lead Status Transitions: "confidence < 50%" → "lead_completeness below threshold"
- Quality metrics table: "Confidence value" → "lead_completeness value"
- Related Concepts: added [[analyses/delivery-integration-layer]] entry

---

## [2026-04-22] analysis | Delivery and Integration Layer

- File created: [[wiki/analyses/delivery-integration-layer.md]]
- Covers: chat interface (primary delivery surface), notifications, dashboards, CRM sync, external API + webhooks, report delivery
- Sources consulted: [[sources/2026-lead-intelligence-engine-reference]], [[sources/2026-intelligence-layer-design]], [[sources/2026-core-business-entities]]
- Related analyses: [[analyses/orchestration-layer-spec]] (handoff point — delivery begins when pipeline_stage = 'delivered'), [[analyses/governance-observability-layer]] (feedback loop and notification_delivery entity)

### Key decisions documented

- Chat is the primary delivery surface — lead cards, HOT alerts, SLA breach alerts, team lead recommendations, and proactive check-ins all delivered in chat
- HOT leads get immediate push notification; WARM/COLD get ranked list delivery only
- Four S1 delivery entities confirmed: `dashboard_definition`, `notification_delivery`, `delivery_endpoint`, `report_definition`
- `delivery_endpoint` is the config record for every external integration (CRM, webhook) — scoped by tenant_id, credentials via vault reference
- CRM push: HOT and WARM pushed immediately; COLD timing TBD; human_review and failed leads not pushed
- Webhook payload signed with HMAC-SHA256; endpoints must use HTTPS
- Delivery failures do not roll back Pipeline 1 — score and lineage are already persisted
- RBAC-scoped access across every surface (admin · team_lead · salesperson · viewer)
- Report cadences: weekly (team lead) + monthly (team lead + product owner) — content pulled from quality_snapshots

### Open decisions recorded
- Alert delivery channel for SLA breaches and recommendations (chat / email / both) — TBD
- Dashboard tooling (in-product vs external BI) — TBD
- Report format (PDF / HTML / inline chat) — TBD
- CRM sync for COLD bucket (immediate vs daily batch) — TBD
- Bidirectional CRM sync for outcome data — recommended for Month 2+
- Full list: Section 12 of the analysis doc

- Index updated with new analysis entry

---

## [2026-04-22] schema-update | Closing stale analyses — confidence-scoring-brainstorm and orchestration-layer-dependencies

- Files updated: wiki/analyses/confidence-scoring-brainstorm.md, wiki/analyses/orchestration-layer-dependencies.md
- confidence-scoring-brainstorm: status changed IN PROGRESS → RESOLVED. Resolution section added at top. Final answer: no confidence score, only `lead_completeness` (float 0.0–1.0). Brainstorm history preserved. One open item remains: threshold value for needs_review.
- orchestration-layer-dependencies: rewritten with resolution status per blocker. All S1/S2 items resolved except `signal.detection_rule` format. Old terminology (Agent E, Phase 00–06, pipeline_log, `confidence` field) mapped to current names. Confirmed as superseded by orchestration-layer-spec.

---

## [2026-04-22] schema-update | Completing orchestration-layer-spec and governance-observability-layer with S1 + S2 deliverables

- Files updated: wiki/analyses/orchestration-layer-spec.md, wiki/analyses/governance-observability-layer.md
- Based on: [[sources/2026-intelligence-layer-design]] (S2) + [[sources/2026-core-business-entities]] (S1)

### orchestration-layer-spec.md — what was completed

1. **Scoring Agent output schema** — locked by S2. Replaced placeholder JSON with the actual ScoringOutput fields: `score` (int), `bucket` (lowercase), `reasoning` (one-line string), `lead_completeness` (float 0.0–1.0), `sub_scores` (object), `recommended_action`, `needs_review` (bool), `schema_version`, `prompt_version`, `model`. Full field-by-field explanation added.
2. **ICP Agent schema** — updated to show ICP feeds into PersonaObject.icp; stored as `ideal_customer_profile` entity by S1; versioned via `ideal_customer_profile_version`. TBD removed.
3. **Signal entities** — updated to confirm `signal` and `signal_evaluation` are formal S1 entities. `detection_rule` format still the one remaining open item.
4. **Lead completeness routing** — replaced "Confidence routing" with "Lead completeness routing". Explained what needs_review means, how the Output Schema Layer sets it, and what "human review queue" actually is (filtered view of leads, not a separate table).
5. **pipeline_stage values** — locked. S1 implements exactly: captured → fetched → enriched → normalised → scored → delivered / human_review / failed.
6. **pipeline_log → three-entity model** — replaced single-table description with pipeline_run + task_execution + lineage_record. Field tables added for each. `confidence` → `lead_completeness` in lineage fields.
7. **Section 9 hard blockers** — all resolved except `detection_rule` format. Resolved: pipeline_stage values, data store entities, Scoring Agent schema, PersonaObject, ICP, signal entities, human_review_queue.
8. **Section 10 open decisions** — marked resolved items, added lead completeness threshold and sub_scores field count as new open items.
9. **Section 11 confirmed decisions** — added 8 new confirmed decisions from S1/S2.

### governance-observability-layer.md — what was completed

1. **"confidence distribution" monitoring metric** — updated to "lead completeness distribution" throughout. Clarified it measures enrichment completeness, not LLM certainty.
2. **pipeline_log schema** — replaced single-table TBD with the three-entity model: pipeline_run, task_execution, lineage_record. Each entity explained in plain English with its specific question it answers.
3. **Lineage section** — updated to name the three entities; explained how audit and lineage relate in the new model.
4. **attributed_feedback table** — updated: `dimension_scores JSONB` → `sub_scores JSONB`; `explanation_reasons TEXT[]` → `reasoning TEXT`; `confidence INTEGER` → `lead_completeness NUMERIC(4,3)`. Field notes added explaining each change.
5. **Pattern detection** — `confidence` band → `lead_completeness` band; example output updated.
6. **Section 8 tables map** — expanded to include full S1 entity list referenced throughout the doc.
7. **Section 9 open questions** — resolved items marked; `leads.assigned_to` remains the one unresolved S1 item; added lead completeness threshold as new TBD.
8. **Section 10 confirmed decisions** — added 10 new confirmed decisions from S1/S2.

### One remaining open item
`signal.detection_rule` format — S2's design document explicitly lists this as an unresolved decision. Lead Enrichment stage code cannot be written until this is locked. Everything else is unblocked.

---

## [2026-04-22] ingest | Intelligence Layer Design + Core Business Entity Catalog

- Files: raw/assets/intelligence_layer_design.docx + raw/assets/core_business_entity.docx
- Wiki pages (sources): [[wiki/sources/2026-intelligence-layer-design]], [[wiki/sources/2026-core-business-entities]]
- Concepts created: [[wiki/concepts/intelligence-layer]], [[wiki/concepts/signal-types]], [[wiki/concepts/data-entity-model]]
- Concepts updated: [[wiki/concepts/persona-layer]] (added Persona Engine details, data model backing, versioning confirmation), [[wiki/concepts/confidence-first-class]] (major correction — see below)
- Overview, index, and log updated
- **Key correction applied:** The intelligence layer design doc uses the term "confidence" for an LLM output field. The user confirmed this is **not a confidence score** — it is a **lead completeness score**. The `needs_review` routing logic and the 3-band threshold gate are unchanged, but the input is lead data completeness rather than LLM self-assessed certainty. This correction propagates through: `confidence-first-class` concept (status updated, calculation section rewritten), `intelligence-layer` concept (ScoringOutput schema field renamed to `lead_completeness`), `overview.md` (correction noted in What's Changed), and both new source pages.
- Notes: Documents are related — intelligence_layer_design.docx defines the layer that produces `lead_score`; core_business_entity.docx defines the entity that stores it. Cross-references wired throughout. Signal entity schema (detection_rule format) remains a hard blocker; noted in both the data entity concept page and the updated open questions list.

---

## [2026-04-19] schema-update | Full Documentation Audit — Governance Structure, Orchestration KPI Integration, Diagrams

- Files updated: wiki/analyses/governance-observability-layer.md, wiki/analyses/orchestration-layer-spec.md
- Supporting updates: wiki/overview.md, index.md, wiki/concepts/lead-pipeline-architecture.md

### governance-observability-layer.md — 3 structural defects fixed

1. **Duplicate Section 5** — Feedback Loops and Quality Tracking were both numbered Section 5. Fixed: Feedback Loops = Section 5, Quality Tracking = Section 6. Section 1 table already had the correct numbering; the body now matches it.
2. **Wrong subsection numbering inside Quality Tracking** — sub-sections read `6.2`, `6.3`, `6.4` while parent heading was Section 5. Fixed: parent renamed to Section 6; subsection `5.1 Approach` renamed to `6.1 Approach`; `6.2/6.3/6.4` were already correct after parent rename.
3. **Wrong section ordering** — Feedback Loops was buried after Security Controls (Section 7) and New Tables (Section 8). Fixed: Feedback Loops moved to Section 5, directly after Lineage (Section 4). Dependency order is now: Monitoring → Auditability → Lineage → Feedback Loops → Quality Tracking → Security.

### governance-observability-layer.md — how/why reasoning added throughout all 6 domains

- **Section 1:** Why governance is a separate layer (not in pipeline critical path); why the 6 domains are ordered the way they are (dependency chain — each section can reference the one before it)
- **Section 2:** Why each monitoring metric exists; why alert thresholds are not set before Month 1 baseline
- **Section 3:** Why two audit surfaces not one — `pipeline_log` (what system did) vs `access_log` (what user did) answer fundamentally different questions; mixing makes both unqueryable
- **Section 4:** Why lineage must be built before the second LLM agent (retrofit cost grows as ~n² due to interlocking concurrent state, not n×); why one table serves both lineage and audit purposes
- **Section 5:** Why feedback loops exist (system degrades silently without them); why 3-step not 1-step (raw thumbs down is useless without attribution; attribution without pattern detection produces overreaction); why attribution fires immediately not weekly; why weekly fixed-count threshold not daily rate-based; why 5 team lead action options; why the loop is slow by design
- **Section 6:** Why SQL jobs against existing tables (no new infrastructure = no new sync problem); why 3 cadences not 1 (per-run answers operational health, weekly answers salesperson behaviour, monthly answers business value — different time horizons); why thresholds set after Month 1
- **Section 7:** Why 3 security layers (each defends different failure mode: code bugs / identity spoofing / privilege misuse); why 4 RBAC roles not 2 or 10; why PII encrypted but scores are not; why credentials in vault not DB; why soft deletes during normal operation

### orchestration-layer-spec.md — 4 KPI cross-reference gaps closed

1. **Quality tracking row (Section 5 table)** — added `[[analyses/scoring-quality-metrics]]` link
2. **Global KPIs paragraph (Section 5)** — added paragraph naming all 3 Global KPIs, who reviews each, at what cadence, and what a drop in System Health means operationally
3. **Confidence routing (Stage 5 Bucketize)** — added "Why this threshold" column to routing table; added paragraph connecting the 3 confidence bands to the per-run confidence distribution KPI and its alert trigger
4. **Lineage writes (Section 8.5)** — added paragraph stating lineage is the data foundation for all quality metrics; added field-by-field table mapping each lineage field to the specific quality metrics that depend on it

### orchestration-layer-spec.md — 2 new diagrams added

1. **Section 2 System Architecture (updated)** — governance box expanded to show: lineage write arrows from both pipelines; Quality Tracking sub-layer with 3 cadence columns (PER-RUN / WEEKLY / MONTHLY); quality_snapshots merge point; 3 Global KPI outputs (System Health, Business Health, Tenant Health Rate); team lead review note and config-back-to-orchestrator arrow
2. **Section 5.1 Quality Metrics Orchestration Flow (new)** — full lifecycle diagram from pipeline run end → per-lead lineage in pipeline_log → 3 SQL job cadences → quality_snapshots → Global KPIs (with WHO and WHEN annotated per KPI) → team lead + product owner review → two recalibration paths (bucket threshold via AP1/AP2; feedback-driven via weight/prompt/ICP re-run) → back to ORCHESTRATOR with specific config fields updated. Includes "How to read" table and rationale for why the loop is intentionally slow.

### Concepts explained in session (not previously documented)

- **Scoring Agent concurrency cap (recommend: 5)** — why a cap exists (rate limits + cost control); how the queue works (5 always running, next enters as one finishes); why 5 is the starting recommendation
- **Timeout threshold for concurrency guard (recommend: 15–30 min)** — what problem it solves (distinguishing active processing from crashed run); why too short causes unnecessary retries; why too long causes recovery delay; why 15-30 min sits safely above any realistic healthy stage duration

---

## [2026-04-19] schema-update | Orchestration Layer Spec — Final Document Rewrite

- File rewritten: wiki/analyses/orchestration-layer-spec.md
- Purpose: full rewrite into plain English, readable in one go, with proper diagrams
- Diagrams added: system architecture (orchestrator + two pipelines + governance), Pipeline 1 fan-out (6-stage with parallel lead processing), fill-in-the-blanks prompt mechanism (before/after signal slot filling)
- All three S3 pillars fully documented: Controller, Tool Invocation, State Tracking
- All confirmed decisions, open decisions, and S1/S2 hard + soft blockers retained
- Removed: redundant internal explanations, excessive sub-headers, verbose normalisation rule lists
- Structure: 11 sections — What it is → Architecture → Pipeline 2 → Pipeline 1 → Governance → Controller → Tool Invocation → State Tracking → S1/S2 contracts → Open decisions → Confirmed decisions
- Status remains: COMPLETE

---

## [2026-04-19] schema-update | Orchestration Layer Spec — COMPLETE

- File updated: wiki/analyses/orchestration-layer-spec.md
- Status: IN PROGRESS → COMPLETE (tool invocation envelope proposed; pending S1/S2 confirmation)
- Section 5.1 fixed: "3-role RBAC" → "4-role RBAC (admin, team_lead, salesperson, viewer)"
- Section 5.1 fixed: Feedback loops row updated from `[TBD]` to reference governance-observability-layer Section 5
- Index updated: orchestration-layer-spec status updated to COMPLETE

**Full document coverage (Subtask 3 — S3):**
- Section 1: Purpose & Scope
- Section 2: Architecture Overview — two pipelines, 4 LLM agents
- Section 3: Pipeline 2 (Onboarding — Onboarding Agent, ICP Agent, Signal Agent)
- Section 4: Pipeline 1 (Event/Lead — Data Gather, Lead Enrichment, Normalise, Scoring Agent, Bucketize)
- Section 5: Governance Layer (cross-cutting — reference to full governance doc)
- Section 6: Orchestration Controller Responsibilities (Pipeline 2 + Pipeline 1 orchestration, cross-pipeline coordination)
- Section 7: Tool Invocation (capability registry, standard envelope, retry policies)
- Section 8: State Tracking (stage transitions, stage update rule, concurrency guard, lineage writes, run-level state, crash recovery)
- Section 9: Interface Contracts Needed (hard + soft blockers for S1/S2)
- Section 10: Open Questions
- Section 11: Confirmed Decisions

---

## [2026-04-19] schema-update | Governance Layer — Proactive Tenant Check-In + Open Questions Fix

- File updated: wiki/analyses/governance-observability-layer.md
- Section 5.7 added: Proactive Tenant Business Check-In
  - Scheduled check-in via existing chat interface (cadence TBD: 2-week or monthly range)
  - Recipient: team_lead of the tenant (TBD — confirm with team)
  - Response handling: 4-step flow — natural language response → Intent Classifier → no change / minor update / significant change
  - Significant change → ICP + Signal Agent re-run (Pipeline 2) with team lead approval
  - Check-in event logged to access_log
  - Rule: system suggests, human approves. Never automatic. [LOCKED principle]
  - Connection to Add-on 8 (deferred): check-in is proactive schedule-driven; Add-on 8 is data-pattern-driven — both use same chat surface and same principle
- Pipeline 2 re-run triggers in orchestration-layer-spec.md updated to document both mechanisms (check-in + feedback-driven)
- Open Questions section fixed: mislabeled "## 6. Quality Tracking" renamed to "## 9. Open Questions"
- 4 new TBDs added to Open Questions: check-in cadence, check-in recipient, message wording, flagging threshold (N)
- Confirmed Decisions updated:
  - "3 roles" → "4 roles: admin, team_lead, salesperson, viewer"
  - Added: team_lead tenant-scoped decision
  - Added: proactive check-in confirmed decisions (3 rows)

---

## [2026-04-19] schema-update | Governance Layer — Feedback Loop + 4-Role RBAC

- File updated: wiki/analyses/governance-observability-layer.md
- Status updated: IN PROGRESS → COMPLETE
- Feedback loop fully documented (Section 5):
  - 3-step enforcement loop: attribution (immediate) → pattern detection (weekly) → team lead action
  - Attribution extracts from lineage: signal_version, prompt_version, fired_signals, dimension_scores, explanation_reasons, confidence
  - New table: attributed_feedback (enriched feedback with lineage data)
  - Pattern detection: groups by signal_version, prompt_version, fired_signals, explanation_reasons
  - Flagging threshold: [TBD — fixed count approach confirmed]
  - Action on pattern: re-run ICP + Signal Agent (not full Pipeline 2, not Signal only)
  - Other actions: adjust weight manually, update prompt template, investigate, dismiss
  - System suggests, human approves — never automated [LOCKED]
  - Recommendations sent to: Team Lead role (tenant-scoped)
- RBAC updated: 3 roles → 4 roles
  - Added: team_lead (tenant-side, scoped to own tenant; receives enforcement recommendations)
  - Existing: admin, salesperson, viewer
  - user_roles CHECK constraint updated
- Duplicate security section removed; section numbering corrected

---

## [2026-04-19] analysis | Governance and Observability Layer

- Wiki page: [[wiki/analyses/governance-observability-layer]]
- Domains documented: monitoring, auditability, lineage, quality tracking, security controls
- Feedback loops: deferred to next discussion
- Key decisions:
  - Quality tracking: scheduled SQL jobs against existing Postgres tables; 3 cadences (per-run, weekly, monthly); results to `quality_snapshots` table; no new infrastructure
  - Alert thresholds: `[TBD — after Month 1 baseline]`
  - Security — 3-layer model:
    - Layer 1: Postgres RLS on every tenant-scoped table (enforced at DB level)
    - Layer 2: JWT with tenant_id + role claims (1h expiry + refresh)
    - Layer 3: 3-role RBAC (admin, salesperson, viewer)
  - Credentials: secrets vault (AWS Secrets Manager or HashiCorp — TBD); never in DB or code
  - PII: encrypted at rest (phone, email, name, address)
  - Audit: pipeline_log (transformations) + access_log (user actions) — two surfaces
  - Soft deletes only during normal operation; hard deletes only during archival
  - Retention policy: `[TBD — per jurisdiction]`
- New tables added: `access_log`, `quality_snapshots`, `user_roles`
- Governance layer failure must not halt Pipeline 1 or Pipeline 2

---

## [2026-04-19] schema-update | Architecture Revision — Two-Pipeline Model + Playbook Integration

- Files updated: wiki/analyses/orchestration-layer-spec.md, wiki/concepts/lead-pipeline-architecture.md, wiki/concepts/agent-vs-tool-classification.md, wiki/overview.md
- Source added: raw/assets/lead_intelligence_manual_enrichment_playbook (1).docx (referenced, not formally ingested)
- Key changes from original single-pipeline architecture:
  - Two pipelines confirmed: Pipeline 2 (Onboarding — one-time per tenant), Pipeline 1 (Event/Lead — per lead)
  - LLM agent count: 1 → 4 (Onboarding Agent, ICP Agent, Signal Agent in Pipeline 2; Scoring Agent in Pipeline 1)
  - Per-lead LLM cost preserved: still 1 LLM call per lead (Scoring Agent only)
  - Signal extraction is deterministic (TOOL), not LLM — separation of extraction vs scoring
  - Prompt mechanism: fill-in-the-blanks template; Signal Agent creates slots, Lead Enrichment fills values
  - Bucket thresholds updated: 75/45 → 80/55/0 (playbook values; tenant-configurable starting points)
  - Pipeline 1 stage order confirmed: event → data gather → lead enrichment → normalise → scoring → bucketize
  - Governance Layer added as explicit cross-cutting layer (monitoring, auditability, lineage, feedback, quality, security)
  - 10 enrichment dimensions documented from playbook (digital footprint, social/web, company intelligence, transactional behavior, intent signals, behavioral sequence, geo/context, psychographic proxy, network/referrals, external triggers)
- New open questions surfaced: signal detection_rule format, Pipeline 2 re-run triggers, 4-agent LLM cost estimate

---

## [2026-04-19] analysis | Orchestration Layer — Responsibilities Specification (IN PROGRESS)

- Wiki page: [[wiki/analyses/orchestration-layer-spec]]
- Deliverable: Subtask 3 — Orchestration Controller, Tool Invocation, State Tracking
- Audience: S1 (data layer) and S2 (intelligence layer) developers
- Confirmed design decisions:
  - Run model: mixed-mode (batch at Agent A, per-lead fan-out for B→C→D→E, single-threaded aggregation at Phase 06)
  - Cross-lead parallelism: included from v2.0 (not deferred); concurrency cap on Agent E [TBD recommend 5]; shared rate limiter across fan-out
  - Concurrency guard: status-based (not DB locks); non-terminal + recent = skip; non-terminal + stale = resume; timeout_threshold [TBD recommend 15-30 min]
  - Stage update rule: pipeline_stage is the final atomic write after lineage + output_data written
  - Lineage writer: orchestrator (not tools); written after every tool call, every phase
  - Crash recovery: resume from current pipeline_stage; 2-retry budget per stage; Agent E re-invocation accepted tradeoff
  - Background jobs (decay, SLA tracker, feedback collector): NOT in orchestrator primary flow
  - Agent E retry policy: 2-attempt with per-failure-mode handling; route to human_review_queue on exhaustion
  - Capability registry: resolved once at Phase 00; zero orchestrator changes per new use case
- Proposed (needs S1/S2 confirmation): tool invocation standard envelope (input/output shape)
- Hard blockers still open: pipeline_stage values (S1), pipeline_log schema (S1), Agent E output JSON schema incl. confidence field (S2)
- Status: IN PROGRESS — crash recovery and tool envelope pending final discussion confirmation

---

## [2026-04-17] analysis | Orchestration Layer — Dependency Analysis

- Wiki page: [[wiki/analyses/orchestration-layer-dependencies]]
- Question: What must S1 (data layer) and S2 (intelligence layer) devs complete before subtask 3 (orchestration layer) can be defined?
- Context: Story = Define System Layer; user is assigned subtask 3
- Hard blockers identified (3): `leads` pipeline_stage field values, `pipeline_log` schema, Agent E output schema (especially confidence field format)
- Soft blockers (4): tenant_config fields, persona object structure, Agent D output format, Agent E failure modes
- Key finding: orchestrator sits between both layers and cannot be designed without knowing the interface contracts on both sides

---

## [2026-04-17] analysis | Scoring Quality Metrics — Global KPIs Section Added

- File updated: wiki/analyses/scoring-quality-metrics.md
- Added Global KPIs section at end of document
- 3 global KPIs: System Health (Pipeline Coverage + Score Stability), Business Health (Scoring Lift + HOT Response Rate), Tenant Health Rate (composite, blocked until Month 1 baseline)
- Written for non-technical readers — plain language, no jargon
- Pairs kept separate within each KPI to prevent hidden failures from averaging

---

## [2026-04-17] schema-update | Scoring Quality Metrics — Universal Formula Rewrite

- File updated: wiki/analyses/scoring-quality-metrics.md
- All formulas rewritten using plain descriptive names — no Greek symbols, no subscript notation, no set operators
- Formulas now self-explanatory at first glance for any audience
- Variable sections retained for data source context
- Metrics without a single formula retain their explanation of why plus a plain-language calculation method

---

## [2026-04-17] schema-update | Scoring Quality Metrics — Mathematical Formula Pass

- File updated: wiki/analyses/scoring-quality-metrics.md
- All formulas rewritten in mathematical notation with named variables
- Every variable explained with its data source
- Metrics without a single formula: AP2 Part 1 (relational check), AP3 (completeness formula pending count vs weight decision), C3 (blocked on TBD thresholds — skeleton formula provided), C5 (deterministic engineering check — no statistical formula appropriate), AR3 (distribution — formula given per-lead, then three aggregates), AR4 (breakdown — per-type formula given, no pass/fail formula), AR5 (session definition pending team decision)
- One open decision surfaced: AP3 completeness formula needs count-based vs weight-based decision from team

---

## [2026-04-17] schema-update | Accuracy Proxy — AP2 + AP3 Combined

- Files updated: wiki/analyses/scoring-quality-metrics.md, wiki/analyses/accuracy-proxy-metrics.md
- Change: AP2 (Monotonicity Check, diagnostic) and AP3 (Discrimination Ratio, primary) merged into single primary metric AP2 (Bucket Separation)
- AP3 slot reassigned to Completeness Qualifier (previously AP4)
- Reason: both metrics used same BOR values and were always read together; separating them was artificial

---

## [2026-04-17] analysis | Scoring Quality Metrics — Combined Document

- Wiki page: [[wiki/analyses/scoring-quality-metrics]]
- Contains: Score Coverage Rate (new) + Accuracy Proxy + Consistency + Action Relevance
- Each section is self-contained; nothing moved between groups
- Score Coverage Rate added as prerequisite health check before the three sub-stories
- Individual group files (accuracy-proxy-metrics.md, consistency-metrics.md, action-relevance-metrics.md) retained separately

---

## [2026-04-17] analysis | Action Relevance — Metric Group Card

- Wiki page: [[wiki/analyses/action-relevance-metrics]]
- Part of story: Define scoring quality metrics → sub-story: action relevance
- Primary metrics: AR1 SLA Compliance Rate, AR2 Action Rate by Bucket
- Diagnostic checks: AR3 Time-to-Action Distribution, AR4 Action Type Distribution by Bucket, AR5 Salesperson Priority Alignment
- Open decision: WARM SLA cutoff needs to be locked (48h or 72h) before AR1 can be calculated
- Targets: TBD — product owner and team leads to set after Month 1 data
- Notes: All three scoring quality sub-stories now complete

---

## [2026-04-17] analysis | Consistency — Metric Group Card

- Wiki page: [[wiki/analyses/consistency-metrics]]
- Part of story: Define scoring quality metrics → sub-story: consistency
- Primary metrics: C1 Cross-Run Bucket Stability, C2 Temporal Score Drift
- Diagnostic checks: C3 Boundary Flip Rate (blocked on TBD thresholds), C4 Decay-Rescore Coherence, C5 Signal Contribution Consistency (engineering check)
- Targets: TBD after Month 1 baseline
- Notes: C3 shares the same bucket threshold blocker as confidence-scoring-brainstorm; C5 should be a unit test at build time

---

## [2026-04-17] analysis | Accuracy Proxy — Metric Group Card

- Wiki page: [[wiki/analyses/accuracy-proxy-metrics]]
- Part of story: Define scoring quality metrics → sub-story: accuracy proxy
- Structure: metric group card (no individual KPI cards); primary metrics + diagnostic checks
- Primary metrics: AP1 Bucket Outcome Rate (per bucket), AP3 Discrimination Ratio (BOR_HOT / BOR_COLD)
- Diagnostic checks: AP2 Monotonicity (pass/fail), AP4 Completeness Qualifier (pass/fail)
- Positive outcome definition: any one of — responded, meeting booked, qualified, deal closed, thumbs up; treated equally
- Targets: TBD after Month 1 baseline
- Notes: success-metrics-framework.md and success-metrics-brief.md found deleted from filesystem; noted in index

---

## [2026-04-17] analysis | Success Metrics Brief — Stakeholder Version Created

- Wiki page: [[wiki/analyses/success-metrics-brief]]
- Trigger: User request — full framework is too long to present to a boss; condensed version needed
- Action: New file created; existing framework untouched
- Same 12 metrics, same 4 dimensions, same 2 hard targets
- Each metric reduced to 2-4 sentences: why it exists, what the calculation does, where any number comes from
- Links back to [[analyses/success-metrics-framework]] for full detail

---

## [2026-04-17] analysis | Success Metrics Framework — v3 Full Explanatory Rewrite

- Wiki page: [[wiki/analyses/success-metrics-framework]]
- Trigger: User review — previous versions listed metrics without explaining why each exists or how calculations work
- Action: Full rewrite in plain English; every metric explains its WHY, every calculation explains its basis, every threshold explains where it comes from and why that number
- Structure retained: 4 dimensions (Scoring Quality, Accuracy Proxy, Consistency, Action Relevance), 12 metrics, 2 hard targets (CO1 ≥90%, CO2 ≤5pt)
- Key explanations added: ground truth problem (why accuracy is measured via proxies), why bucket boundaries are guesses not data-derived, why 5pt is the CO2 limit, why feedback is tracked per bucket not overall, why decay-rescore coherence matters, why SLA windows are tenant-capacity-dependent
- Blockers still documented: bucket score boundaries (most urgent), human review SLA window, CRM data source, feedback loop go-live

---

## [2026-04-17] analysis | Confidence Scoring Brainstorm

- Wiki page: [[wiki/analyses/confidence-scoring-brainstorm]]
- Status: IN PROGRESS — user not yet clear, discussion to resume
- What was established:
  - Signals + weights are per-tenant, per-persona (dev team configures)
  - Three types of uncertainty exist: data, signal contradiction, boundary proximity
  - Enrichment-based confidence (weighted signal coverage) is circular — ruled out
  - Boundary proximity is the only thing confidence can add that enrichment score doesn't
- What changed: confidence-first-class.md marked UNDER REVIEW; previous 2026-04-16 decision on calculation method reopened
- Blocker: bucket thresholds (HOT/WARM/COLD score boundaries) are TBD — confidence formula cannot be finalised without them
- Next step: define bucket boundaries, then resume confidence discussion

---

## [2026-04-16] schema-update | Confidence Calculation + Metrics Framework Revised

**Change 1 — confidence-first-class.md**
- Resolved TBD: confidence is derived from enrichment score threshold, not LLM self-reported
- Reasoning: LLMs are poorly calibrated at self-reporting certainty; deterministic calculation is more reliable
- Routing logic unchanged; only the calculation method is now decided

**Change 2 — success-metrics-framework.md**
- Replaced over-engineered v1 (25+ metrics, assumption-based targets, statistical formulas) with lean v2
- 12 metrics across 4 dimensions, split by when data is actually available
- No targets set upfront except 2 hard operational ones (CO1 prompt coverage, CO2 cross-run stability)
- Removed: ECE, KL divergence, shadow re-runs, 4-tier hierarchy, 25-scenario edge case catalogue
- Added: guiding principle — measure first, set targets after Month 1 baseline
- Index: updated

---

## [2026-04-14] analysis | Success Metrics Framework
- Wiki page: [[wiki/analyses/success-metrics-framework]]
- Question: Define measurable product KPIs — scoring quality, accuracy proxy, consistency, action relevance
- Structure: 4-tier hierarchy (North Star → Health Scorecard → Diagnostic → Infrastructure), 4 dimensions + Meta, 25 catalogued edge cases, 8 open decisions
- Tier 0 candidates: A2 (HOT:COLD Conversion Ratio ≥2.5×), D5 (Per-Salesperson Lift ≥+20% median)
- Top decision recommendation: adopt Curiosity Budget (5% COLD leads called weekly) and capture pre-launch baseline — both structurally unrecoverable if skipped
- Index: updated (1 analysis added)

---

## [2026-04-14] ingest | Multi-Tenant Adaptive Lead Intelligence Engine — Master Reference
- File: raw/assets/lead_intelligence_engine_reference.md
- Wiki page: [[wiki/sources/2026-lead-intelligence-engine-reference]]
- Entities created: gamoft, urvee-organics, govmen, anishekh (4 new)
- Concepts created: lead-pipeline-architecture, agent-vs-tool-classification, persona-layer, confidence-first-class, lineage-log, disqualification-gate, score-decay, action-sla, capability-registry, feedback-loop, adaptive-signal-lifecycle (11 new)
- Overview: updated with domain, thesis, themes, open questions
- Index: updated (1 source, 4 entities, 11 concepts)
- Notes: First source. Domain is Lead Intelligence Engine POC for Gamoft. ~50 TBDs open across technology stack, tenant personas, DB schemas, and algorithm decisions. Adaptive Signal Lifecycle (Add-ons 6/7/8) explicitly deferred to Sprint 2-3.

---

## [2026-04-14] session-start | Initial Setup
- Schema: CLAUDE.md created
- Structure: wiki/, wiki/sources/, wiki/entities/, wiki/concepts/, wiki/analyses/, raw/, raw/assets/ created
- Index: index.md initialized (0 sources)
- Notes: Fresh vault. Awaiting domain selection and first source ingest.
