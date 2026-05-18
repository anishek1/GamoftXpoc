---
type: analysis
question: "How are prompt templates versioned, stored, activated, and managed across tenants and pipeline runs?"
date: 2026-05-18
tags: [prompt, orchestration, versioning, prompt-registry, lifecycle, rollback, multi-tenant, caching]
sources_consulted:
  - "[[analyses/context-construction-specification]]"
  - "[[analyses/prompt-template-framework]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[concepts/persona-layer]]"
  - "[[analyses/llm-operational-safeguards]]"
status: COMPLETE
---

# Prompt Orchestration Framework

**System:** Multi-Tenant Adaptive Lead Intelligence Engine  
**Version:** 1.0.0  
**Date:** 2026-05-18

**Scope:** Prompt template versioning, the `prompt_registry` data model, prompt lifecycle (draft → active → deprecated), version selection at runtime, rollback, and multi-tenant prompt management.

**Out of scope:** Prompt content and structure (see [[analyses/prompt-template-framework]]), context assembly mechanics (see [[analyses/context-construction-specification]]), LLM operational safeguards (see [[analyses/llm-operational-safeguards]]).

---

## 1. Storage Architecture — Resolved Decision

Prompt storage uses a **hybrid model**:

| Component | Where stored | Updated by | Deployment required? |
|---|---|---|---|
| Scoring rubric, output format rules, model rules | **Code (git-versioned)** | Engineering — requires PR and deployment | Yes |
| Assembled system message per tenant | **Database (`prompt_registry`)** | Persona Agent (automated) | No |
| Tenant persona, ICP, signal weights | **Database (`prompt_registry`)** | Persona Agent (automated) | No |

**Why hybrid:** System-level rules (scoring rubric, JSON output schema) change rarely and must be reviewed before changing — git provides audit trail and PR review. Tenant-specific content changes on every Persona Agent re-run — requiring a deployment for each tenant's persona update is operationally unacceptable.

**Consequence:** Two change triggers require two different version increment types (see §3).

---

## 2. `prompt_registry` Data Model

One row per `(tenant_id, prompt_template_version)` pair. This table is the authoritative store for all assembled system messages.

```
prompt_registry
├── tenant_id              uuid          NOT NULL
├── prompt_template_version string       NOT NULL   (semver e.g. "v1.2.0")
├── persona_version        string        NOT NULL   (persona version active when assembled)
├── system_message_text    text          NOT NULL   (full assembled system message — immutable)
├── signal_count           integer       NOT NULL   (number of signals in this version)
├── input_token_count      integer       NOT NULL   (measured at assembly time)
├── status                 string        NOT NULL   ('draft' | 'active' | 'deprecated')
├── created_at             timestamptz   NOT NULL
├── created_by             string        NOT NULL   ('persona_agent' | 'system')
├── activated_at           timestamptz   NULLABLE
├── deprecated_at          timestamptz   NULLABLE
└── deprecated_reason      string        NULLABLE

CONSTRAINTS:
  - UNIQUE (tenant_id, prompt_template_version)
  - Only ONE row per tenant_id may have status = 'active' at any time
```

**Immutability:** `system_message_text` is write-once. Once a row is inserted, the text field is never updated. Corrections require a new version row.

---

## 3. Version Numbering

Format: `v<MAJOR>.<MINOR>.<PATCH>` — semantic versioning.

| Change type | Version segment | Trigger | Who increments |
|---|---|---|---|
| Scoring rubric change, output schema change, model rules change | **MAJOR** | Engineering decision; requires deployment | Engineering, via code change |
| Persona Agent re-run (new persona, ICP, or signals) | **MINOR** | Persona Agent on re-run completion | Persona Agent (automated) |
| Wording correction in system message | **PATCH** | Team lead decision | Engineering or team lead via tooling |

**Rule:** A MAJOR version increment resets MINOR and PATCH to 0 for all tenants. Every tenant gets a new active version at the next Persona Agent run after a MAJOR increment.

**Rule:** MINOR and PATCH increments are per-tenant. Tenant A at `v1.5.0` and Tenant B at `v1.2.0` are both valid simultaneously.

---

## 4. Prompt Version Lifecycle

```
                 ┌─────────────────────────────────────────────────────┐
                 │                   prompt_registry                    │
                 │                                                      │
                 │  [DRAFT]  ──── team lead approves ──►  [ACTIVE]     │
                 │                                             │        │
                 │  Persona Agent writes                       │        │
                 │  new version here                   new version      │
                 │  (status = draft)                   activates        │
                 │                                             │        │
                 │                                             ▼        │
                 │                                       [DEPRECATED]   │
                 │                                   (previous active)  │
                 │                                                      │
                 └─────────────────────────────────────────────────────┘
```

### State Transitions

| From | To | Trigger | Who |
|---|---|---|---|
| — | `draft` | Persona Agent completes a re-run and writes new prompt | Persona Agent (automated) |
| `draft` | `active` | Team lead reviews and approves in governance UI | Team Lead |
| `active` | `deprecated` | New version is activated (system auto-deprecates previous active) | System (automated on activation) |
| `active` | `deprecated` | Rollback (see §6) — previous version is restored to active | Team Lead |

**Approval gate:** No `draft` version is ever used for live scoring. The Prompt Layer always loads the `active` version only. Draft versions can be used for shadow scoring or manual testing.

**New tenant:** A new tenant's first prompt version is created and auto-activated (no approval gate on first run — no prior version to compare against, no production impact).

---

## 5. Runtime Version Selection

At the start of every Pipeline 1 run:

1. Orchestrator requests the active prompt version for `tenant_id` from `prompt_registry`
2. `prompt_registry` returns the single row where `(tenant_id = X AND status = 'active')`
3. If no active row exists → `PersonaNotFoundError` (hard failure)
4. Orchestrator passes `prompt_template_version` to the Prompt Layer
5. Prompt Layer loads `system_message_text` for this exact version
6. `prompt_template_version` is stored in `lineage_record` after the call

**No version lookup per lead.** The version is loaded once at the start of each pipeline run (or batch). All leads in the same run use the same version. Mid-run version changes (Persona Agent re-run completing while a batch is running) do not affect the in-flight batch — they apply to the next pipeline run.

---

## 6. Rollback Procedure

Rollback is available when a newly activated prompt version produces scores that diverge from expected behaviour.

**Trigger:** Team lead or admin observes anomalous scoring quality metrics (AP2 monotonicity failure, C1 bucket instability) and initiates rollback.

**Rollback steps:**
1. Set current `active` version status to `deprecated` (with `deprecated_reason = 'rollback'`)
2. Set the previous `deprecated` version status back to `active`
3. Record the rollback event in `lineage_record` with `reason = 'rollback'` and both version identifiers
4. Optionally: trigger rescore for leads scored under the bad version (team lead decision)

**Constraint:** Only one rollback level is supported — rollback restores the immediately previous version. There is no multi-level rollback at MVP. If a rollback is needed beyond one step, a new Persona Agent re-run is required.

**Rescore on rollback:** Rolling back a prompt version does not automatically rescore affected leads. The team lead must explicitly trigger rescore for the affected `tenant_id` for leads scored during the bad-version window. Rescore uses the `rescore` prompt variant (see [[analyses/prompt-template-framework]] §4).

---

## 7. Multi-Tenant Scoping

Each tenant has an independent prompt version lifecycle. One tenant's re-run or rollback does not affect any other tenant.

| Operation | Scope |
|---|---|
| Persona Agent re-run | Single `tenant_id` — creates a new draft version for that tenant only |
| Rollback | Single `tenant_id` — restores previous version for that tenant only |
| MAJOR system version bump | All tenants — each tenant's next Persona Agent re-run will incorporate the new major version |

**MAJOR version propagation:** After a MAJOR version increment (engineering deployment), the new scoring rubric and output format are in code but tenant-specific prompt templates in `prompt_registry` still reference the old MAJOR version. Tenants are migrated at their next scheduled Persona Agent re-run. Until migration, the old template continues to work with the old code version — **backward compatibility is required for at least one MAJOR version window.** Engineering must maintain the previous MAJOR version's scoring rubric in code until all tenants have migrated.

---

## 8. Prompt Template Generation After Persona Agent

After Persona Agent Step 3 completes (signal definitions locked), the Orchestrator generates the prompt template. This is an **AUTOMATION** step — not an LLM call.

**Steps:**
1. Load all signals for `tenant_id` from `signal` table, sorted alphabetically by `signal_name` per dimension
2. Generate system message text by injecting PersonaObject + IcpDefinition + signal list into the standard four-section template (see [[analyses/prompt-template-framework]])
3. Measure token count of the assembled system message
4. Check token count against the tenant's tier limit (see [[analyses/context-construction-specification]] §7)
5. Write to `prompt_registry` with `status = 'draft'`
6. Notify team lead for approval

If token count exceeds limit at step 4 → halt; alert team lead; request reduction in signal count or ICP text length. Persona Agent outputs are not discarded — only the prompt generation is blocked until configuration is corrected.

---

## 9. Observability

Every prompt version activation, deprecation, and rollback is recorded. The following signals are emitted:

| Event | Where recorded | Fields |
|---|---|---|
| Version activated | `prompt_registry.activated_at` + audit log | `tenant_id`, `version`, `approved_by` |
| Version deprecated | `prompt_registry.deprecated_at` + `deprecated_reason` | `tenant_id`, `version`, `reason` |
| Rollback | `lineage_record` + audit log | `tenant_id`, `reverted_from_version`, `reverted_to_version`, `reason` |
| Scoring call | `lineage_record` | `prompt_template_version` (per-call attribution) |

The feedback loop uses `prompt_template_version` from `lineage_record` to attribute scoring patterns to specific prompt versions. See [[analyses/governance-observability-layer]].

---

## Open Decisions

| Decision | Status |
|---|---|
| Tooling for team lead prompt approval (governance UI vs manual DB update) | TBD — post-MVP; manual DB update acceptable for 3-tenant POC |
| Automatic rescore trigger on rollback | TBD — team decision; not implemented at MVP |
| MAJOR version backward-compatibility window length | TBD — recommend one MAJOR version window (until all tenants re-run) |
| Shadow scoring (run draft and active in parallel for comparison) | Deferred to post-MVP |
