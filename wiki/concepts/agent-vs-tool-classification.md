---
type: concept
name: "Agent vs Tool Classification"
aliases: ["Add-on 1", "LLM vs Tool", "component classification"]
tags: [architecture, cost-control, classification, add-on-1]
source_count: 1
last_updated: 2026-04-19
---

# Agent vs Tool Classification

## Definition

Every component in the pipeline is explicitly tagged as either **LLM_AGENT** (uses an LLM for judgment-based output) or **TOOL** (executes deterministic, rule-based logic).

- **LLM_AGENT**: uses an LLM, produces judgment/reasoning/personalization. Expensive, variable, slower.
- **TOOL**: deterministic code. Cheap, consistent, fast, debuggable.

## Updated Classification — 4 LLM Agents `[TEAM DECISION 2026-04-19]`

The original source doc stated 1 LLM agent. The team has decided on a two-pipeline architecture with 5 LLM agents total (4 original + Message Parser). Pipeline 2 agents are one-time per tenant setup. Per-lead: 1 Sonnet call (Scoring Agent, all paths) + 1 Haiku call (Message Parser, DM path only). Lead Ad events use only the Sonnet call. — Updated 2026-05-03.

### Pipeline 2 — Onboarding (One-Time Per Tenant)

| # | Component | Type | Reasoning |
|---|---|---|---|
| 1 | Onboarding Agent | LLM AGENT | Interprets tenant business context to create persona |
| 2 | ICP Agent | LLM AGENT | Defines ideal customer profile from persona |
| 3 | Signal Agent | LLM AGENT | Creates signal definitions from persona + ICP; decides signal count per dimension |

### Pipeline 1 — Event/Lead (Per Lead)

| # | Component | Type | Reasoning |
|---|---|---|---|
| 1 | Orchestrator | TOOL | Deterministic workflow engine |
| 2 | Intent Classifier | TOOL | Rule/small-model mapping |
| 3 | Tenant Config Load | TOOL | DB fetch |
| 4 | Persona Load | TOOL | DB fetch |
| 5 | Signal Definitions Load | TOOL | DB fetch |
| 6 | Confirmation UX | TOOL | Templated message |
| 7 | Data Gather (Agent A equiv.) | TOOL | API calls + dedup + rate limits |
| 7b | Pre-Filter Gate (DM path only) | TOOL | Drops spam/noise before parsing; Lead Ad events skip |
| **7c** | **Message Parser (DM path only)** | **LLM AGENT** | **Haiku; multilingual + typo-tolerant extraction from raw DM text; Lead Ad events skip** |
| 8 | Rate Limiter | TOOL | Quota checks |
| 9 | Deduplicator | TOOL | Matching algorithm |
| 10 | Lead Enrichment | TOOL | Data addition (CRM, public web) + deterministic signal extraction |
| 11 | Normaliser | TOOL | Schema transformation + conflict resolution |
| 11b | Intent Gate | TOOL | Pause/pass check: very_low intent + HIGH fit → awaiting_clarification; all others pass |
| 12 | Prompt Template Filler | TOOL | Inserts extracted signal values into pre-written template |
| **13** | **Scoring Agent** | **LLM AGENT** | **Holistic lead judgment using filled prompt template** |
| 14 | Output Validator | TOOL | Schema check on Scoring Agent output |
| 15 | Disqualification Gate | TOOL | Rule-based critical overrides |
| 16 | Bucketing | TOOL | Threshold comparison (80/55/0) |
| 17 | SLA Tracker | TOOL | Time-based alerts |
| 18 | Score Decay Job | TOOL | Scheduled background job |
| 19 | Feedback Collector | TOOL | Event ingestion |
| 20 | Observability Logger | TOOL | Metrics emission |
| 21 | Governance Layer | TOOL | Cross-cutting monitoring, auditability, security |

**Total: 5 LLM AGENTS, 23+ TOOLS** (updated 2026-05-03: +Message Parser)

## Updated Cost Principle

Original: "1 LLM agent in the entire pipeline" — updated to:

**"Scoring Agent (Sonnet) runs for every lead on all paths. Message Parser (Haiku) runs on the DM path only — cheaper than Sonnet, skipped entirely for Lead Ad events. Pipeline 2 agents (Onboarding, ICP, Signal) are one-time per tenant setup — their cost is amortised across all leads that tenant ever processes."**

## Why Signal Extraction Is a TOOL (Not LLM)

Signal definitions from Pipeline 2 are explicit enough (name, description, detection_rule) to be evaluated deterministically against enriched lead data. Keeping extraction as a TOOL means:

- Scoring Agent (Sonnet) per lead + Message Parser (Haiku) on DM path only — cost stays predictable and bounded
- Extraction bugs (wrong signal value) are debuggable separately from scoring bugs (wrong judgment)
- Consistent, reproducible results across leads

## Why Each LLM Agent Is Justified

| Agent | Why LLM is needed |
|---|---|
| Onboarding Agent | Must interpret open-ended business description into structured persona |
| ICP Agent | Must reason about who an ideal customer is from business context |
| Signal Agent | Must decide what signals are relevant and how many; creative and domain-specific |
| Scoring Agent | Must weigh 5 dimensions simultaneously against persona+ICP, produce calibrated confidence |

## Tensions & Contradictions

- Original `[LOCKED]` principle of "1 LLM agent" is superseded by team decision on two-pipeline architecture + Message Parser addition (2026-05-03). Updated principle: Sonnet call per lead (all paths) + Haiku call on DM path only. Pipeline 2 LLM calls are one-time setup.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — the two-pipeline system this classification applies to
- [[concepts/persona-layer]] — produced by Onboarding Agent (LLM)
- [[concepts/confidence-first-class]] — output of Scoring Agent (LLM)

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 03, 14, 19.1
- Team decision 2026-04-19 — two-pipeline architecture, 4 LLM agents
