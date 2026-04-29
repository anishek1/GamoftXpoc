---
last_updated: 2026-04-22
source_count: 3
---

# Wiki Index

**Last updated:** 2026-04-22 | **Sources ingested:** 3

*This file is maintained by the Wiki Agent. Do not edit manually.*

---

## Overview
- [[wiki/overview]] — Current synthesis: Lead Intelligence Engine pre-planning; 1 source, ~50 TBDs open

---

## Sources

- [[wiki/sources/2026-lead-intelligence-engine-reference]] — Master pre-planning reference for Multi-Tenant Adaptive Lead Intelligence Engine v2.0 (Gamoft) | ingested: 2026-04-14
- [[wiki/sources/2026-intelligence-layer-design]] — Intelligence Layer design spec: 4-component pipeline, score_lead() interface, 5 scoring dimensions, 6 open decisions | ingested: 2026-04-22
- [[wiki/sources/2026-core-business-entities]] — Full data entity catalog: 32 entities across lead lifecycle, governance, and operational observability | ingested: 2026-04-22

---

## Entities

- [[wiki/entities/gamoft]] — Organization; builder and B2B self-tenant of the Lead Intelligence Engine; owner: Anishekh | sources: 1
- [[wiki/entities/urvee-organics]] — Organization; B2C POC tenant (organic products); Instagram + WhatsApp channels | sources: 1
- [[wiki/entities/govmen]] — Organization; third POC tenant; profile entirely TBD | sources: 1
- [[wiki/entities/anishekh]] — Person; document owner and project lead at Gamoft | sources: 1

---

## Concepts

- [[wiki/concepts/lead-pipeline-architecture]] — Two-pipeline architecture; Pipeline 2 onboarding, Pipeline 1 per-lead; serial build order | sources: 1
- [[wiki/concepts/intelligence-layer]] — 4-component internal pipeline (Persona Engine → Prompt Layer → Rating Agent → Output Schema Layer); score_lead() interface; 60s timeout | sources: 1
- [[wiki/concepts/signal-types]] — 5 scoring dimensions: Fit 25%, Intent 25%, Engagement 20%, Behaviour 20%, Context 10%; backed by signal + signal_evaluation entities | sources: 2
- [[wiki/concepts/data-entity-model]] — 32 entities in 3 groups: core lead lifecycle, governance & quality, operational observability | sources: 1
- [[wiki/concepts/agent-vs-tool-classification]] — Add-on 1; 4 LLM agents (3 Pipeline 2, 1 Pipeline 1); 1 LLM call per lead | sources: 1
- [[wiki/concepts/persona-layer]] — Add-on 2; rich per-tenant business profile; built by Persona Engine; versioning confirmed | sources: 2
- [[wiki/concepts/confidence-first-class]] — Add-on 3; CORRECTED 2026-04-22: lead completeness score (not LLM confidence); 3-band routing; threshold TBD | sources: 2
- [[wiki/concepts/lineage-log]] — Non-negotiable audit trail; per lead per step; backed by lineage_record entity | sources: 1
- [[wiki/concepts/disqualification-gate]] — Add-on 4a; score gates before bucketing (serviceability, geo, role) | sources: 1
- [[wiki/concepts/score-decay]] — Add-on 4b; background job: -10/7d, -20/14d, auto-cold/30d | sources: 1
- [[wiki/concepts/action-sla]] — Add-on 4c; HOT=24h, WARM=2-3d, COLD=weekly; breach → team lead alert | sources: 1
- [[wiki/concepts/capability-registry]] — Maps use case → agent list; zero orchestrator changes per new capability | sources: 1
- [[wiki/concepts/feedback-loop]] — 3-step enforcement; backed by feedback_record entity | sources: 1
- [[wiki/concepts/adaptive-signal-lifecycle]] — Add-ons 6/7/8 DEFERRED; integrity scoring + discovery + business-language UX | sources: 1

---

## Analyses

- [[wiki/analyses/scoring-quality-metrics]] — Combined scoring quality metrics document; Score Coverage Rate + Accuracy Proxy (AP1–AP4) + Consistency (C1–C5) + Action Relevance (AR1–AR5) | date: 2026-04-17 | status: complete
- [[wiki/analyses/action-relevance-metrics]] — Action relevance metric group card; AR1 SLA Compliance, AR2 Action Rate by Bucket, AR3 Time-to-Action Distribution, AR4 Action Type Distribution, AR5 Salesperson Priority Alignment | date: 2026-04-17 | status: complete
- [[wiki/analyses/consistency-metrics]] — Consistency metric group card; C1 Cross-Run Bucket Stability, C2 Temporal Score Drift, C3 Boundary Flip Rate (blocked), C4 Decay-Rescore Coherence, C5 Signal Contribution Consistency | date: 2026-04-17 | status: complete
- [[wiki/analyses/accuracy-proxy-metrics]] — Accuracy proxy metric group card; AP1 BOR, AP2 Monotonicity, AP3 Discrimination Ratio, AP4 Completeness Qualifier; part of scoring quality metrics story | date: 2026-04-17 | status: complete
- [[wiki/analyses/confidence-scoring-brainstorm]] — RESOLVED 2026-04-22: no confidence score; field is lead_completeness (float 0.0–1.0) set by Output Schema Layer; threshold for needs_review still TBD | date: 2026-04-17
- [[wiki/analyses/governance-observability-layer]] — Governance layer: 6 domains in dependency order (monitoring → auditability → lineage → feedback loops → quality tracking → security); full how/why reasoning throughout; 3-step feedback loop (attribution → pattern detection → team lead action); 3-layer security (RLS + JWT + 4-role RBAC); why/how for every design decision | date: 2026-04-19 | status: COMPLETE
- [[wiki/analyses/orchestration-layer-spec]] — Subtask 3 responsibilities spec: two-pipeline architecture, 4 LLM agents, fill-in-the-blanks prompt, deterministic signal extraction, bucket thresholds 80/55/0; updated system architecture diagram shows full KPI layer inside governance; Section 5.1 Quality Metrics Orchestration Flow shows full pipeline-to-KPI-to-recalibration lifecycle; 4 cross-references to scoring-quality-metrics wired in | date: 2026-04-19 | status: COMPLETE
- [[wiki/analyses/orchestration-layer-dependencies]] — SUPERSEDED 2026-04-22: all S1/S2 blockers resolved except signal.detection_rule format; old terminology mapped to current names; see orchestration-layer-spec for current state | date: 2026-04-17
- [[wiki/analyses/delivery-integration-layer]] — Delivery and Integration Layer: chat interface (primary), notifications, dashboards, CRM sync, external API/webhooks, report delivery; 4 S1 delivery entities; RBAC-scoped access per surface; 16 open decisions | date: 2026-04-22 | status: COMPLETE
- [[wiki/analyses/service-scaling-strategy]] — Service scaling strategy for Ingestion, Orchestration+LLM, and Reporting services; pool model at MVP; per-tenant concurrency caps; quality_snapshots read rule; tiering framework; LLM cost metering; based on Tod Golding O'Reilly book | date: 2026-04-24 | status: COMPLETE
- [[wiki/analyses/execution-type-classification]] — Classifies every workflow step as AUTOMATION / AGENT / HYBRID; 3 AGENT steps (Pipeline 2 LLM agents), 1 HYBRID step (Scoring — Rating Agent + banding enforcement), all others AUTOMATION; includes test strategy, debug, cost, and observability implications | date: 2026-04-26 | status: COMPLETE
- [[wiki/analyses/persona-agent-spec]] — Persona Agent full specification: inputs (tenant description, re-run context), 3 sequential LLM steps (business persona → ICP → signal definitions), outputs (PersonaObject, IcpDefinition, signal[]), invocation conditions, failure handling; naming distinction from Persona Engine | date: 2026-04-26 | status: COMPLETE
- [[wiki/analyses/signal-detection-rule-spec]] — Signal detection_rule format: NormalisedEvent schema, named extractor + params model, 13 extractor types, 5 worked examples, strategy-pattern execution model | date: 2026-04-28 | status: COMPLETE — resolves last hard blocker for Lead Enrichment code
- [[wiki/analyses/lead-enrichment-architecture]] — Master enrichment + investigation doc: signal-separation principle; two-phase model (sync Tier 1+2, async investigation); India-specific provider stack (Truecaller, Google Places, GST, MCA, JustDial, IndiaMART, Apollo, Instagram); B2B vs B2C investigation paths; NormalisedEvent field expansion; 6 new extractor types; cost model ~$180–270/mo; PDL on hold | date: 2026-04-30 | status: COMPLETE
- [[wiki/analyses/channel-integration-layer]] — How tenants connect platforms via OAuth (Meta, LinkedIn, website snippet); channel_connection entity; webhooks + polling hybrid event detection; per-platform payload normalisation; token lifecycle management | date: 2026-04-28 | status: COMPLETE
- ~~wiki/analyses/enrichment-provider-stack~~ — **MERGED** into lead-enrichment-architecture 2026-04-30; all content preserved there | date: 2026-04-28 | status: DELETED
- [[wiki/analyses/tech-stack-research]] — Complete production technology stack research: 10 categories fully researched, all locked decisions documented, 3 open decisions pending team input (Temporal vs Step Functions, Pusher vs Soketi, Aurora vs EC2 PostgreSQL), two full-budget scenarios (Managed ~$357/mo, Hybrid ~$288/mo), LLM cost estimate ~$27/mo steady state | date: 2026-04-26 | status: COMPLETE — 3 items pending team decision
- [[wiki/analyses/rating-agent-spec]] — Rating Agent full specification: inputs (EnrichedLead, signal_values, variant), score output, reasoning output, completeness output (lead_completeness — not LLM confidence), full ScoringOutput schema, per-tenant concurrency cap, failure handling, observability signals | date: 2026-04-26 | status: COMPLETE
- [[wiki/analyses/future-optional-agents]] — Recommendation Agent (personalized outreach, unlock after Month 3) and Workflow Agent (lifecycle orchestration, unlock after Month 6) defined as post-MVP extensions; unlock conditions per quality metric; principles for future agent expansion | date: 2026-04-26 | status: COMPLETE
- ~~wiki/analyses/success-metrics-framework~~ — **DELETED** from filesystem 2026-04-26; log entries preserved; covered by scoring-quality-metrics combined doc | date: 2026-04-17 | status: DELETED
- ~~wiki/analyses/success-metrics-brief~~ — **DELETED** from filesystem 2026-04-26; stakeholder condensed version of success-metrics-framework; log entries preserved | date: 2026-04-17 | status: DELETED
