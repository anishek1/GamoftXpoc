---
type: analysis
question: "What information must be completed by the devs working on subtask 1 (data layer) and subtask 2 (intelligence layer) before I can define the orchestration layer (subtask 3)?"
date: 2026-04-17
tags: [orchestration, system-layer, dependencies, subtask-3]
sources_consulted: [sources/2026-lead-intelligence-engine-reference]
---

# Orchestration Layer — What I Need from Subtask 1 and Subtask 2

**Question:** What information must be completed by the devs working on subtask 1 (data layer) and subtask 2 (intelligence layer) before I can define the orchestration layer (subtask 3)?  
**Date:** 2026-04-17  
**Context:** Story: Define System Layer. Subtask 3 = Orchestration Controller, Tool Invocation, State Tracking.

---

## Answer / Finding

The Orchestrator is a TOOL (deterministic workflow engine — see [[concepts/lead-pipeline-architecture]]) and the only surface the user ever interacts with. It sits between the data layer and the intelligence layer — it reads/writes state from the data layer and calls components from the intelligence layer in order. Because of this position, it cannot be designed without knowing what those two layers look like at their interfaces.

---

## What I Need from Subtask 1 (Data Layer)

**1. `leads` table schema — specifically the `pipeline_stage` field**

The orchestrator drives the lead through 7 status transitions:
`captured → fetched → gathered → normalised → prompt_ready → enriched → delivered`

It reads and writes this status at every step. Without knowing the exact field name, accepted values, and how to query by lead ID, the state tracking logic cannot be written.

**2. `pipeline_log` table schema**

Every step the orchestrator runs must write a lineage entry (non-negotiable per [[concepts/lineage-log]]). Known fields from the reference doc: `run_id, lead_id, agent_id, input_snapshot, output_snapshot, duration_ms, error` — but all are `[TBD]`. The S1 dev must finalize this before the orchestrator can write lineage.

**3. `tenant_config` table schema**

The orchestrator loads tenant config at Phase 00 before anything else. It needs to know what fields come back so it can validate the config, halt on missing/malformed data (LOCKED rule), and pass the right things to downstream tools.

**4. Where does scored output get written?**

When Agent E finishes, the orchestrator writes the final scored lead back somewhere. Is that the `leads` table, a separate output table, or both? The S1 dev must decide this. Without it, the orchestrator's final write step cannot be defined.

---

## What I Need from Subtask 2 (Intelligence Layer)

**1. Agent E output schema — specifically the `confidence` field**

The orchestrator uses confidence to route every lead:
- ≥80% → auto-bucket
- 50–79% → flag for review
- <50% → human review queue

This routing logic is the core of the orchestrator's decision-making in Phase 05/06. Without knowing the exact field name, format (integer 0–100? float 0–1?), and what else is in the output object, this cannot be written.

**2. Persona object structure from the persona engine**

The orchestrator loads the persona in Phase 00 and passes it to Agent D. It needs to know the exact structure of what the persona engine returns. The reference doc has a JSON skeleton (Section 15.2) but field values are all `[TBD]`. The S2 dev must lock the schema.

**3. What Agent D hands off to Agent E**

The orchestrator sequences Agent D → Agent E. It needs to know what Agent D produces (the assembled prompt payload) so it can correctly pass it. If the format changes, the orchestrator breaks.

**4. Agent E failure modes**

The reference doc notes that output validation logic is `[TBD]` (Section 10.4). When Agent E returns malformed JSON or fails, the orchestrator must decide: retry, halt, or flag. The S2 dev must define what failure looks like so the orchestrator can handle it.

---

## Hard Blockers vs. Soft Blockers

**Cannot proceed without these (hard blockers):**
- `leads` table `pipeline_stage` field — exact values (from S1)
- `pipeline_log` schema — exact fields (from S1)
- Agent E output schema — especially `confidence` field name and format (from S2)

**Can stub with assumptions, but must flag them (soft blockers):**
- `tenant_config` field list
- Persona object structure
- Agent D output format
- Agent E failure modes

---

## Caveats & Gaps

- All table schemas are explicitly `[TBD]` in the reference doc (Section 13.2) — one ticket per table is the planned approach
- Agent E output JSON schema is `[TBD]` (Section 10.4) — this is the single most important unresolved item for the orchestrator
- The `human_review_queue` table is also `[TBD]` existence — if confidence <50% routes there, the orchestrator needs to know how to write to it

## Follow-up Questions

- Has the S1 dev started on the `leads` and `pipeline_log` table schemas yet?
- Has the S2 dev locked the Agent E output JSON structure?
- Is `human_review_queue` confirmed as a table or will it be handled differently?
