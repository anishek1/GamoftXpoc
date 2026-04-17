---
last_updated: 2026-04-14
source_count: 1
---

# Wiki Index

**Last updated:** 2026-04-14 | **Sources ingested:** 1

*This file is maintained by the Wiki Agent. Do not edit manually.*

---

## Overview
- [[wiki/overview]] — Current synthesis: Lead Intelligence Engine pre-planning; 1 source, ~50 TBDs open

---

## Sources

- [[wiki/sources/2026-lead-intelligence-engine-reference]] — Master pre-planning reference for Multi-Tenant Adaptive Lead Intelligence Engine v2.0 (Gamoft) | ingested: 2026-04-14

---

## Entities

- [[wiki/entities/gamoft]] — Organization; builder and B2B self-tenant of the Lead Intelligence Engine; owner: Anishekh | sources: 1
- [[wiki/entities/urvee-organics]] — Organization; B2C POC tenant (organic products); Instagram + WhatsApp channels | sources: 1
- [[wiki/entities/govmen]] — Organization; third POC tenant; profile entirely TBD | sources: 1
- [[wiki/entities/anishekh]] — Person; document owner and project lead at Gamoft | sources: 1

---

## Concepts

- [[wiki/concepts/lead-pipeline-architecture]] — 7-phase 8-stage 22-component pipeline; serial build order; 1 LLM agent | sources: 1
- [[wiki/concepts/agent-vs-tool-classification]] — Add-on 1; 1 LLM agent (Agent E), 21 tools; cost + reliability principle | sources: 1
- [[wiki/concepts/persona-layer]] — Add-on 2; rich per-tenant business profile; the competitive moat | sources: 1
- [[wiki/concepts/confidence-first-class]] — Add-on 3; confidence as user-visible field; 3-band routing logic | sources: 1
- [[wiki/concepts/lineage-log]] — Non-negotiable audit trail; per lead per step; must build before 2nd agent | sources: 1
- [[wiki/concepts/disqualification-gate]] — Add-on 4a; score gates before bucketing (serviceability, geo, role) | sources: 1
- [[wiki/concepts/score-decay]] — Add-on 4b; background job: -10/7d, -20/14d, auto-cold/30d | sources: 1
- [[wiki/concepts/action-sla]] — Add-on 4c; HOT=24h, WARM=2-3d, COLD=weekly; breach → team lead alert | sources: 1
- [[wiki/concepts/capability-registry]] — Maps use case → agent list; zero orchestrator changes per new capability | sources: 1
- [[wiki/concepts/feedback-loop]] — v1: one-tap thumbs; three-layer version (Add-on 6) deferred to Sprint 2-3 | sources: 1
- [[wiki/concepts/adaptive-signal-lifecycle]] — Add-ons 6/7/8 DEFERRED; integrity scoring + discovery + business-language UX | sources: 1

---

## Analyses

- [[wiki/analyses/scoring-quality-metrics]] — Combined scoring quality metrics document; Score Coverage Rate + Accuracy Proxy (AP1–AP4) + Consistency (C1–C5) + Action Relevance (AR1–AR5) | date: 2026-04-17 | status: complete
- [[wiki/analyses/action-relevance-metrics]] — Action relevance metric group card; AR1 SLA Compliance, AR2 Action Rate by Bucket, AR3 Time-to-Action Distribution, AR4 Action Type Distribution, AR5 Salesperson Priority Alignment | date: 2026-04-17 | status: complete
- [[wiki/analyses/consistency-metrics]] — Consistency metric group card; C1 Cross-Run Bucket Stability, C2 Temporal Score Drift, C3 Boundary Flip Rate (blocked), C4 Decay-Rescore Coherence, C5 Signal Contribution Consistency | date: 2026-04-17 | status: complete
- [[wiki/analyses/accuracy-proxy-metrics]] — Accuracy proxy metric group card; AP1 BOR, AP2 Monotonicity, AP3 Discrimination Ratio, AP4 Completeness Qualifier; part of scoring quality metrics story | date: 2026-04-17 | status: complete
- [[wiki/analyses/confidence-scoring-brainstorm]] — Confidence calculation brainstorm; enrichment-based confidence ruled out as circular; boundary-proximity proposed but not locked; bucket thresholds needed | date: 2026-04-17 | status: IN PROGRESS

**Note:** wiki/analyses/success-metrics-framework.md and wiki/analyses/success-metrics-brief.md were deleted from the filesystem (visible in git status). Log entries exist but files are gone.
