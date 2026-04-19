# Wiki Log

*Append-only. Most recent entries at top.*

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
