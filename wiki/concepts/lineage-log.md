---
type: concept
name: "Lineage Log"
aliases: ["pipeline_log", "audit trail", "lead lineage"]
tags: [observability, audit, non-negotiable, lineage]
source_count: 1
last_updated: 2026-04-14
---

# Lineage Log

## Definition

An **immutable audit trail** written per lead, per agent step. Every transformation in the pipeline produces a lineage entry. This is explicitly called "non-negotiable" in the source document and must be built before the second agent is added — not retrofitted after all 8 agents are built.

## What Is Logged Per Step

- `agent_id` — which component produced this entry
- `timestamp` — when
- `tenant_id` — which tenant
- `lead_id` — which lead
- Input state snapshot — what the agent received
- Output state — what the agent produced
- Prompt version used (Agent D/E only)
- Confidence score at this step

## Storage

`pipeline_log` table in Postgres. Field-level schema is `[TBD]` (one ticket). Known fields from pre-planning:
- `run_id`, `lead_id`, `agent_id`, `input_snapshot`, `output_snapshot`, `duration_ms`, `error`

Alternative: dedicated table vs object storage for snapshots — `[TBD]`.

## Why It Matters

Without lineage, you cannot:
- Know which agent is slow
- Know which source is failing
- Know whether scoring quality is drifting over time
- Debug a bad score retroactively
- Run meaningful A/B tests on prompt changes

**"Observability turns a working prototype into a maintainable production system."**

The cost of building lineage is low when the system is small. Cost of retrofitting with 8 running agents is enormous.

## Build Rule `[LOCKED]`

Build the lineage log **before** adding the second agent — not after the eighth.

## Relationship to Other Systems

The deferred [[concepts/adaptive-signal-lifecycle]] (Add-ons 6/7/8) runs entirely off the lineage log. It is the data source for:
- Signal accuracy audits
- Integrity scoring
- Discovery of new signal patterns from mis-bucketed leads

## Evidence & Examples

- "Build lineage logging BEFORE adding the second agent, not after the eighth. Cost is low early, enormous when retrofitting." (source: [[sources/2026-lead-intelligence-engine-reference]])
- All three layers of the deferred feedback architecture read from the same lineage log. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None. The build-first rule is explicitly locked.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — lineage written at every phase
- [[concepts/adaptive-signal-lifecycle]] — depends entirely on lineage data
- [[concepts/feedback-loop]] — reads from lineage for weight tuning

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 02, 10.5, 19.8
