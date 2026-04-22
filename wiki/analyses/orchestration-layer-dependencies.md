---
type: analysis
question: "What information must be completed by the devs working on subtask 1 (data layer) and subtask 2 (intelligence layer) before I can define the orchestration layer (subtask 3)?"
date: 2026-04-17
tags: [orchestration, system-layer, dependencies, subtask-3]
sources_consulted: [sources/2026-lead-intelligence-engine-reference, sources/2026-intelligence-layer-design, sources/2026-core-business-entities]
status: SUPERSEDED — 2026-04-22. All blockers resolved except one. See [[analyses/orchestration-layer-spec]] for the complete, current specification.
---

# Orchestration Layer — Dependencies from S1 and S2

**Question:** What information must be completed by the devs working on subtask 1 (data layer) and subtask 2 (intelligence layer) before the orchestration layer can be defined?  
**Date:** 2026-04-17 | **Updated:** 2026-04-22

---

## Status (2026-04-22)

S1 delivered the data entity catalog (`core_business_entity.docx`). S2 delivered the intelligence layer design (`intelligence_layer_design.docx`). Almost everything is now resolved. This document is retained for historical context. For the current state of all decisions, read [[analyses/orchestration-layer-spec]].

`signal.detection_rule` format is `[TBD]` — will be updated when ready.

---

## What Was Needed from S1 — Resolution Status

**1. `leads` table schema — specifically the `pipeline_stage` field**

The orchestrator drives the lead through stage transitions and reads/writes `pipeline_stage` at every step.

**RESOLVED.** S1's entity catalog confirms the `lead` entity. The accepted `pipeline_stage` values are locked by this orchestration spec:

```
captured → fetched → enriched → normalised → scored → delivered
                                                     → human_review
[any non-terminal] → failed
```

S1 must implement exactly these string values. Any change breaks the orchestrator at runtime.

---

**2. Data store for pipeline execution and lineage**

Every step the orchestrator runs must write a lineage entry. A run-level record is also needed to track overall success.

**RESOLVED.** What was previously described as a single `pipeline_log` is three formal S1 entities:

- `pipeline_run` — one record per complete workflow execution; answers "did the whole run succeed?"
- `task_execution` — one record per stage per run; answers "which stage failed and why?"
- `lineage_record` — data provenance per stage; answers "what went in, what came out, which prompt was used?"

The orchestrator writes to all three after every stage call.

---

**3. `tenant_config` mandatory field list**

The orchestrator loads tenant config before anything else and halts if required fields are missing.

**RESOLVED.** S1's entity catalog defines `tenant` and `business_profile` as formal entities. S2's PersonaObject defines what fields the intelligence layer needs from tenant config: `business_type`, `icp` definition, `scoring_weights`, `banding` rules, `custom_rules`, `tone`. The orchestrator's pre-flight check validates these fields are present before any pipeline stage runs.

---

**4. Where scored output gets written**

When the Scoring Agent finishes, the orchestrator writes the result somewhere.

**RESOLVED.** S1's entity catalog confirms `lead_score` as the formal entity for scoring output, and `score_model_version` as the entity tracking which scoring logic produced it. The orchestrator writes to both. The intelligence layer never writes directly — it returns a ScoringOutput object to the orchestrator, which then persists it.

---

**5. `human_review_queue` — is it a separate table?**

Leads below the completeness threshold need somewhere to go.

**RESOLVED. No separate table.** Human review leads are a filtered view of the `leads` table where `pipeline_stage = 'human_review'`. The `needs_review` flag in the ScoringOutput tells the orchestrator to set that stage value. No extra write needed.

---

## What Was Needed from S2 — Resolution Status

**1. Scoring Agent output schema — specifically the completeness field**

The orchestrator uses this to route every lead after scoring.

**RESOLVED.** S2's intelligence layer design locks the full ScoringOutput schema. Key fields:

```
score              : int (0–100)
bucket             : 'hot' | 'warm' | 'cold'  (lowercase)
reasoning          : str  (one line)
lead_completeness  : float (0.0–1.0)
sub_scores         : { fit, intent, engagement, recency }
recommended_action : str
needs_review       : bool
schema_version     : str
prompt_version     : str
model              : str
```

Note: the field previously described as `confidence` is `lead_completeness`. It is not LLM self-assessed certainty — it measures completeness of the enriched lead data. See [[concepts/confidence-first-class]].

The orchestrator reads `needs_review` to decide routing:
- `needs_review = false` → assign bucket, write to output, set `pipeline_stage = 'delivered'`
- `needs_review = true` → assign bucket, write to output, AND set `pipeline_stage = 'human_review'`

---

**2. Persona object structure (Onboarding Agent output)**

The orchestrator loads this at the start of every Pipeline 1 run and passes it into the scoring call.

**RESOLVED.** S2 defines the PersonaObject:

```
tenant_id       : str
business_type   : 'B2B' | 'B2C'
icp             : IcpDefinition
scoring_weights : { fit, intent, engagement, recency }
banding         : { hot_min, warm_min, cold_max }
custom_rules    : list
tone            : str
version         : int
```

Cached by the Persona Engine with a 15-minute TTL. Cache invalidated when tenant updates scoring rubric. Orchestrator never calls the Persona Engine directly — it passes `tenant_id` and `lead` to `score_lead()` and the intelligence layer handles the rest.

---

**3. What the Prompt Layer produces and how it's passed to the Scoring Agent**

The orchestrator sequences the intelligence layer call. It needs to understand what happens internally.

**RESOLVED.** The orchestrator does not manage this handoff — it's internal to the intelligence layer. The orchestrator calls a single function: `score_lead(tenant_id, lead, variant, ...)` and gets back a ScoringOutput. The Prompt Layer → Rating Agent → Output Schema Layer pipeline is entirely inside the intelligence layer. The orchestrator never touches it.

---

**4. Scoring Agent failure modes**

When scoring fails, the orchestrator must know how to handle it.

**RESOLVED.** S2 defines two typed return values — ScoringOutput (success or needs_review) and ScoringFailure. ScoringFailure carries a `reason` field: `'parse_error'`, `'schema_invalid'`, or `'low_confidence'` (now: low completeness). The intelligence layer never raises an exception — it always returns one of the two types. The orchestrator's retry policy applies to ScoringFailure results (retry once → if still fails → `pipeline_stage = 'human_review'` with `reason: scoring_failed`).

---

**5. Signal `detection_rule` format and evaluation engine**

The Lead Enrichment stage runs detection rules against enriched data to extract signal values.

`[TBD]`

---

## Signal Agent output

**RESOLVED.** The Signal Agent produces `signal` records — one per scoring question, organized by dimension (fit / intent / engagement / behavioral / context). Stored in S1's `signal` entity. The companion `signal_evaluation` entity stores the per-lead answer for each signal question after Lead Enrichment runs. This is the data model backing the fill-in-the-blanks prompt mechanism.

---

## Old Terminology Map

This document originally used terminology from before the two-pipeline design was finalised. Here is the mapping to current terms:

| Old term | Current term |
|---|---|
| Agent E | Scoring Agent |
| Agent D | Prompt Layer (internal to intelligence layer) |
| Phase 00–06 | Pipeline 1 stages: Data Gather → Lead Enrichment → Normalise → Scoring Agent → Bucketize |
| `pipeline_log` (single table) | Three entities: pipeline_run, task_execution, lineage_record |
| `confidence` field | `lead_completeness` field (float 0.0–1.0) |
| enrichment score | lead score (0–100, output of Scoring Agent) |

---

## Summary — What Remains Open

| Item | Status |
|---|---|
| `signal.detection_rule` format + evaluation engine | `[TBD]` |
| Lead completeness threshold for `needs_review` | Team decision — S2 suggests 0.6 or 0.75 |
| `sub_scores` field count (4 listed vs 5 scoring dimensions) | S2 to clarify — soft blocker for orchestrator logging |
| Scoring Agent concurrency cap | Team decision — recommend 5 |
| Concurrency guard timeout threshold | Team decision — recommend 15–30 min |

Everything else is unblocked and documented in [[analyses/orchestration-layer-spec]].
