---
type: concept
name: "Agent vs Tool Classification"
aliases: ["Add-on 1", "LLM vs Tool", "component classification"]
tags: [architecture, cost-control, classification, add-on-1]
source_count: 1
last_updated: 2026-04-14
---

# Agent vs Tool Classification

## Definition

Every component in the pipeline is explicitly tagged as either **LLM_AGENT** (uses an LLM for judgment-based output) or **TOOL** (executes deterministic, rule-based logic). This is Add-on 1 of v2.0, locked in pre-planning.

- **LLM_AGENT**: uses an LLM, produces judgment/reasoning/personalization. Expensive, variable, slower.
- **TOOL**: deterministic code. Cheap, consistent, fast, debuggable.

## Full Component Matrix `[LOCKED]`

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
| **15** | **Agent E — LLM Scorer** | **LLM AGENT** | **Holistic judgment** |
| 16 | Output Validator | TOOL | Schema check |
| 17 | Disqualification Gate | TOOL | Rule-based |
| 18 | Bucketing | TOOL | Threshold comparison |
| 19 | SLA Tracker | TOOL | Time-based alerts |
| 20 | Decay Job | TOOL | Scheduled job |
| 21 | Feedback Collector | TOOL | Event ingestion |
| 22 | Observability Logger | TOOL | Metrics emission |

**Total: 1 LLM AGENT, 21 TOOLS**

## Why It Matters

- LLM calls are expensive, variable, and slow
- Rules are cheap, consistent, and fast
- Minimizing LLM calls to 1 per lead makes the system affordable at scale
- Mixing LLM judgment into tools creates unpredictable costs and hard-to-debug behavior
- The anti-pattern explicitly rejected: "auto-generate subagents" — dynamic LLM agent creation is not production-ready

## Evidence & Examples

- Agent E is the only justified LLM use: it must evaluate a lead holistically against a tenant persona, weigh 5 dimensions simultaneously, and produce confidence-calibrated scores. No rule set can replace this judgment. (source: [[sources/2026-lead-intelligence-engine-reference]])
- Everything upstream of Agent E is data gathering and schema transformation — no judgment required. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

- Intent Classification is currently classified as TOOL, but implementation is `[TBD]` (rules vs small LLM vs hybrid). If a small LLM is used, this classification may need revisiting.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — the pipeline this classification applies to
- [[concepts/persona-layer]] — the reason Agent E specifically needs LLM judgment

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 03, 14, 19.1
