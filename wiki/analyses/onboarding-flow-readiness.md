---
type: analysis
question: "What are the exact conditions that must all be true for onboarding to be complete, Pipeline 1 to be enabled, and the tenant to be considered active?"
date: 2026-05-05
tags: [onboarding, pipeline-1, pipeline-2, tenant-setup, readiness-check, consent, activation]
sources_consulted:
  - "[[concepts/lead-pipeline-architecture]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/channel-integration-layer]]"
  - "[[analyses/onboarding-flow-stage-map]]"
  - "[[sources/2026-core-business-entities]]"
status: COMPLETE — Subtask 3 of 3; resolves deferred consent_preference decision (not a Stage 5 condition); flags tenant.onboarding_complete naming inconsistency in orchestration-layer-spec
---

# Onboarding Flow — Completion Criteria

**Question:** What are the exact conditions that must all be true for onboarding to be complete, Pipeline 1 to be enabled, and the tenant to be considered active?
**Date:** 2026-05-05

---

## Answer / Finding

Two conditions must both be true for Stage 5 (Readiness Check) to pass and `tenant.status` to flip to `active`:

1. **Pipeline 2 fully completed** — PersonaObject, IcpDefinition, signal definitions, and prompt template are all stored
2. **At least one active channel connector** — at least one `channel_connection` record with `status = active`

`consent_preference` is **not** a Stage 5 readiness condition. This Subtask 3 document resolves the deferred decision: `consent_preference` is a per-lead record, enforced per-lead at the Pipeline 1 Consent Gate, and has nothing to verify at tenant activation time (no leads exist yet). See [Section 3](#3-consent_preference-resolution) for the full reasoning.

Both conditions must pass simultaneously. There is no partial activation state.

---

## Scope of This Document

This document owns two distinct concepts that must not be conflated:

| Concept | What it is | Owned by |
|---------|-----------|----------|
| **Stage 5 Activation Check** | One-time gate; runs once at onboarding; flips `tenant.status` to `active` | This document |
| **Pipeline 1 Pre-flight Check** | Per-run guard; runs before every Pipeline 1 execution; verifies scoring config still exists | [[analyses/orchestration-layer-spec]] §6.2 |

The Stage 5 check is what makes scoring *possible* for the first time. The per-run pre-flight is what makes scoring *safe* on every subsequent run. They check overlapping but different things.

---

## 1. Condition 1 — Pipeline 2 Fully Completed

Pipeline 2 is the Persona Agent's three-step LLM sequence. It is complete when all four outputs are persisted:

| Output | Stored in | Check |
|--------|-----------|-------|
| PersonaObject | `personas` table | Record exists for `tenant_id`; `scoring_weights` fields sum to 1.0; `version` field set |
| IcpDefinition | `ideal_customer_profile` entity; embedded in PersonaObject as `icp: IcpDefinition` | Record exists for `tenant_id`; `priority_signals` list is non-empty |
| Signal definitions | `signal` table | At least one signal record per dimension; each dimension's `weight_within_dim` values sum to 1.0 |
| Prompt template | `prompt_registry` | Active template exists for `tenant_id`; one named slot per signal |

**All four must be present.** A PersonaObject without a corresponding prompt template means the Scoring Agent has no fill-in-the-blanks structure to receive. A prompt template without signal definitions means there are no slots to fill.

**Why IcpDefinition has two checks:** The IcpDefinition is embedded in the PersonaObject for fast read at scoring time (zero extra DB read) AND stored separately in `ideal_customer_profile` for versioning and historical attribution. The readiness check validates the PersonaObject contains it — the separate `ideal_customer_profile` record's existence is a Persona Agent constraint, not a separate Stage 5 check.

**What triggers the check:**
- The check triggers automatically when Pipeline 2 finishes (the Persona Agent writes its final output, then the orchestrator triggers Stage 5 evaluation)
- It also triggers when the user manually navigates to Stage 5
- Both paths evaluate the same conditions; whichever fires first wins

**What "Pipeline 2 failed" means for Stage 5:**
If Pipeline 2 halted mid-run (LLM error, weight constraint failure), none of the outputs may be fully written. The check reads whatever is present and fails on the first missing condition. The failure reason shown to the user is specific: *"Scoring setup did not complete — [step name] did not finish successfully. Please review and resubmit your business profile."*

---

## 2. Condition 2 — At Least One Active Channel Connector

| Status | Counts toward activation? | Notes |
|--------|--------------------------|-------|
| `active` | **Yes** | Webhook subscriptions live; events flowing |
| `pending_review` | No | Meta App Review or LinkedIn allowlist pending; no live events |
| `pending_verification` | No | Website connector: snippet installed but no ping received yet |
| `error` | No | Registration failed; polling fallback active but no reliable events |
| `expired` | No | Token expired post-setup; user must reconnect |
| `revoked` | No | User or platform revoked access |

**One partial Meta connection is sufficient.** If Instagram is `active` but Facebook and WhatsApp are in `error`, Stage 5 passes. At least one surface must be `active`.

**Why connectors are required before activation:**
Without an active connector, Pipeline 1's Data Gather step has no channels to fetch from. The event gap window queue (events that arrived during onboarding) only exists because webhooks went live in Stage 4. If no connector ever went active, the queue is empty, and there are no leads to drain. Requiring at least one active connector before activation ensures the system is in a state where leads can actually arrive.

**What triggers the check:**
Condition 2 is not independently triggered — it is always evaluated as part of the Stage 5 check. It cannot pass in isolation. A connector going `active` does not, by itself, trigger Stage 5; Stage 5 re-evaluates both conditions together.

---

## 3. consent_preference Resolution

The [[analyses/onboarding-flow-stage-map]] deferred this decision to Subtask 3 with the note: *"Whether it is user-set or system-defaulted is a decision owned by Subtask 3."*

**Decision: `consent_preference` is not a Stage 5 readiness condition.**

**Reasoning:**

The `consent_preference` entity (source: [[sources/2026-core-business-entities]]) is a per-lead record. The source states: *"even a high-quality HOT lead should only be contacted through allowed and preferred channels. Consent must be checked before any outreach action."* This describes a check on a per-lead basis — for a specific lead's consent to be contacted on a specific channel.

At Stage 5, there are no leads. No `consent_preference` records exist for this tenant yet because no leads have been processed. There is nothing to check. A readiness condition that can never fail is not a condition — it is noise.

The enforcement point is in Pipeline 1, not onboarding: the **Consent Gate** runs before external enrichment for every lead (see [[analyses/orchestration-layer-spec]] §4.3 Stage 2). The Consent Gate reads the lead's consent state (DPDP for India; GDPR for EU/UK) and restricts enrichment and contact channels accordingly. This is where consent is verified — at the moment a real lead arrives, not at tenant activation.

**Implication for the Stage Map:** The Stage 5 diagram in [[analyses/onboarding-flow-stage-map]] shows `consent_preference` as a readiness condition alongside the two confirmed conditions. This is now resolved as incorrect. The Stage Map should be updated to remove `consent_preference` from the Stage 5 activation gate; it is a Pipeline 1 Consent Gate enforcement point, not an onboarding readiness condition.

---

## 4. `tenant.status` State Machine

```
Stage 2 complete
  → tenant.status = onboarding
        ↓
Stage 5: both conditions pass
  → tenant.status = active
        ↓
Stage 5: activation effects fire (see Section 5)
        ↓
[No further transitions in this state machine]
```

**`tenant.status = active` is a one-way transition.** There is no mechanism to set it back to `onboarding`. If a tenant's connectors all go inactive after activation, `tenant.status` stays `active` — the activation state represents "this tenant has completed setup," not "this tenant is currently receiving events."

**What `tenant.status = active` does not mean:**
- It does not mean all connectors are currently active (connectors can go `expired` or `error` after activation)
- It does not mean Pipeline 2 outputs are current (Pipeline 2 can re-run and update them; `tenant.status` is unaffected)
- It does not mean Pipeline 1 is actively running (Pipeline 1 runs on its own trigger schedule or webhook events)

**Pipeline 2 re-run after activation:** When a team-lead-approved Pipeline 2 re-run completes, the new PersonaObject and signal definitions overwrite the existing records. `tenant.status` stays `active` throughout the re-run — Pipeline 1 continues using the old PersonaObject for any in-flight runs. The Persona Engine's 15-minute TTL cache invalidates when the new PersonaObject is written; subsequent Pipeline 1 runs load the updated configuration. There is no activation interruption. (Source: [[analyses/persona-agent-spec]] failure handling; [[concepts/persona-layer]] Persona Engine section.)

---

## 5. Activation Effects — What Happens When Both Conditions Pass

When Stage 5 passes, the orchestrator fires these steps in order:

```
1. tenant.status = active          (atomic write)
         ↓
2. Queue drain initiated           (all captured leads from gap window, FIFO by arrival_at)
         ↓
3. Pipeline 1 enabled for this tenant
         ↓
4. User notification sent          "Your platform is ready. Leads are now being scored."
```

**Queue drain detail:**
- All `lead` + `event` records written during the gap window (i.e., events that arrived while `tenant.status = onboarding`) have `pipeline_stage = captured`
- These records are queued in FIFO order by `arrival_at` timestamp
- On drain, each lead enters Pipeline 1 from the start (Data Gather through Bucketize)
- The drain runs as a background job; the user notification fires as soon as `tenant.status = active`, not when the drain completes

**Why FIFO:** Leads that arrived earlier have had longer wait times. Processing them first preserves intent signal recency — a lead that expressed high intent three days ago is still higher priority than one that arrived an hour ago, but within the queue, earlier arrivals should be handled first to avoid inverting their relative priority.

---

## 6. Failure Handling — Per Condition

### Pipeline 2 Not Complete

| Sub-condition | User-facing message | Next action |
|---------------|---------------------|-------------|
| Pipeline 2 still running | *"Setting up your scoring intelligence — this usually takes under 2 minutes."* | Auto-retry when Pipeline 2 finishes |
| Pipeline 2 failed | *"Scoring setup failed — your business profile needs review."* | Persistent error banner; click navigates to Stage 3 with pre-filled form; user corrects and resubmits; Pipeline 2 re-queued from Step 1 |
| PersonaObject missing required field | Same as Pipeline 2 failed; specific field flagged in admin alert | Same as above |
| Signal dimension weights don't sum to 1.0 | Admin alert; user directed to resubmit | Same as above |

### No Active Connector

| Sub-condition | User-facing message | Next action |
|---------------|---------------------|-------------|
| No connectors connected at all | *"Connect at least one channel before activation."* | User directed to Stage 4 |
| All connectors in `pending_review` | *"Your channel connections are awaiting approval from the platform. Activation will complete automatically once at least one is approved."* | Stage 5 re-evaluates when a connector transitions to `active` |
| All connectors in `error` | *"Your channel connections could not be established. Reconnect at least one to activate."* | User directed to Stage 4 to retry |
| Website connector only, in `pending_verification` | *"Your website connector is not yet verified. Install the snippet on your site and wait for it to go live."* | Stage 5 re-evaluates when verification ping is received |

### Both Conditions Unmet Simultaneously

Stage 5 shows both failure reasons. The user must resolve both before activation will pass — the check does not pass on partial completion.

---

## 7. Edge Cases

**Connector goes inactive after activation:** `tenant.status` stays `active`. Pipeline 1 continues with remaining active connectors. If all connectors are inactive simultaneously, Data Gather returns 0 leads for the next run. An alert fires: *"No active channel connectors — no leads are being received."* The tenant must reconnect at least one connector. There is no `tenant.status` rollback.

**Two Stage 5 triggers fire simultaneously (race condition):** Pipeline 2 completes and the user navigates to Stage 5 at the same moment. Both read the same pre-conditions. Both may attempt to write `tenant.status = active`. This is safe as long as the write is an atomic compare-and-swap: *set status to `active` only if current status is `onboarding`*. The second write is a no-op. Queue drain must also be idempotent: a lead already transitioned out of `pipeline_stage = captured` must not be re-queued.

**Tenant abandons onboarding mid-stage:** No timeout is currently defined. A tenant with `tenant.status = onboarding` can remain in that state indefinitely. If a tenant with a partial `business_profile` never submits Stage 3, their `tenant` record stays in `onboarding` and Pipeline 2 is never queued. This is an operational hygiene gap — a cleanup policy (e.g., archive after 90 days of inactivity) should be defined post-MVP.

**Meta App Review in progress:** A Facebook or Instagram connector may be in `pending_review` for 2–7 days. If WhatsApp or LinkedIn is active, Stage 5 passes immediately using that connector. If Meta connectors are the only ones and all are in `pending_review`, Stage 5 waits. The system must auto-trigger Stage 5 evaluation when any connector transitions from `pending_review` to `active`.

---

## 8. Relationship to Pipeline 1 Pre-flight Check

The per-run pre-flight check (documented in [[analyses/orchestration-layer-spec]] §6.2) is a different check from Stage 5 activation. The two checks answer different questions:

| Check | When | Question it answers | Failure action |
|-------|------|---------------------|----------------|
| Stage 5 Activation | Once, at onboarding | "Is this tenant ready to start receiving and scoring leads?" | Block activation; show specific failure reason |
| Pipeline 1 Pre-flight | Before every Pipeline 1 run | "Does this tenant still have valid scoring config?" | Halt the run; alert admin |

**Overlap:** Both verify that Pipeline 2 outputs exist (PersonaObject, signals, prompt template). But the pre-flight check does not verify connectors — Data Gather just returns 0 leads if no connectors are active, and Pipeline 1 runs with no leads (no-op). The Stage 5 check verifies connectors to ensure Pipeline 1 has something to work with from day one.

**Naming inconsistency:** [[analyses/orchestration-layer-spec]] §6.2 checks `tenant.onboarding_complete = true`. This document uses `tenant.status = active` (standardized in [[analyses/onboarding-flow-stage-map]] v2 correction). They are semantically equivalent — `tenant.status = active` is the canonical field name. The orchestration-layer-spec should be updated: replace `tenant.onboarding_complete = true` with `tenant.status = 'active'` in §6.2 and §6.1 step 7. The `tenant.onboarding_complete` flag does not correspond to any field in the `tenant` entity schema.

---

## Evidence

- Pipeline 2 four-output structure (PersonaObject, IcpDefinition, signal[], prompt template): [[analyses/persona-agent-spec]]
- PersonaObject fields and `scoring_weights` must-sum-to-1.0 constraint: [[analyses/persona-agent-spec]] Step 1
- `channel_connection` entity, status values (active|expired|revoked|error), and polling fallback: [[analyses/channel-integration-layer]]
- Stage 5 readiness as convergence of Pipeline 2 + ≥1 active connector: [[analyses/onboarding-flow-stage-map]] Stage 5
- `consent_preference` as per-lead entity for outreach consent: [[sources/2026-core-business-entities]]
- Consent Gate runs before enrichment per-lead: [[analyses/orchestration-layer-spec]] §4.3 Stage 2
- Pipeline 2 re-run leaves `tenant.status` unchanged; Persona Engine 15-min TTL cache invalidates on new PersonaObject: [[analyses/persona-agent-spec]] invocation conditions; [[concepts/persona-layer]] Persona Engine section
- `pipeline_stage = captured` during gap window; queue drains on `tenant.status = active`: [[analyses/onboarding-flow-stage-map]] Stage 4 (event gap window section)

---

## Caveats & Gaps

- **No defined timeout for `tenant.status = onboarding`:** A tenant can abandon onboarding indefinitely. A cleanup/expiry policy is needed post-MVP.
- **Website connector verification trigger:** No mechanism is defined to auto-trigger Stage 5 re-evaluation when the website snippet ping arrives and `channel_connection.status` flips from `pending_verification` to `active`. The orchestrator must subscribe to `channel_connection.status` changes or poll.
- **`pending_review` auto-trigger:** Same gap — when Meta or LinkedIn flips a connector from `pending_review` to `active`, Stage 5 must be re-evaluated automatically. Requires a status-change event or polling job.
- **Queue drain concurrency:** The gap-window drain is described as FIFO, but no concurrency cap is specified. If a large volume of events accumulated during a long onboarding (e.g., a tenant who left connectors active for a week before completing Pipeline 2), the drain could overwhelm the per-tenant concurrency cap. A drain-specific rate limit or batch size should be defined.
- **Stage Map update needed:** The Stage 5 diagram in [[analyses/onboarding-flow-stage-map]] still shows `consent_preference` as a readiness condition. This should be removed now that Subtask 3 resolves it as not applicable.
- **orchestration-layer-spec update needed:** §6.1 step 7 says "Mark tenant as onboarding_complete." §6.2 checks `tenant.onboarding_complete = true`. Both should be updated to use `tenant.status = 'active'`.

---

## Follow-up Questions

- Should a "graceful degradation" mode exist where a tenant with all connectors expired can still access historical scored leads (read-only), but no new scoring runs fire? Or does this happen automatically since Pipeline 1 simply returns 0 leads?
- Should the system notify the tenant admin when `tenant.status` flips to `active` via email in addition to the in-platform UI notification?
- Is there an SLA for queue drain time after activation? If 1,000 leads accumulated during onboarding, how long should the drain take before the tenant should expect to see results?

---

## Related Documents

- [[analyses/onboarding-flow-stage-map]] — Subtask 1: full stage-by-stage flow; Stage 5 transition trigger
- [[analyses/onboarding-flow-inputs]] — Subtask 2: required user inputs per stage
- [[analyses/persona-agent-spec]] — Pipeline 2 step outputs and failure handling
- [[analyses/orchestration-layer-spec]] — Pipeline 1 pre-flight check (§6.2); Pipeline 2 controller steps (§6.1)
- [[analyses/channel-integration-layer]] — connector status values and lifecycle
- [[sources/2026-core-business-entities]] — `consent_preference` entity definition
