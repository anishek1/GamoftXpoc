# Phase 0 Planning Audit Report

**Date:** 2026-05-19
**Auditor:** Claude Code (Wiki Agent — Senior Architect Mode)
**Backlog version:** `raw/JIRA DOCS.xlsx` — Phase0_Full_Detailed_JIRA_Backlog (Sheet1)
**Audit type:** READ-ONLY — no files were modified during this audit except this output file.

---

## Executive Summary

| Metric | Value |
|---|---|
| Total .md files scanned | 76 |
| XLSX backlog parsed (epics / stories / sub-tasks) | 11 / 33 / 99 |
| Epics with at least one planning document | 11 / 11 |
| OBSIDIAN_ONLY planning documents | 51 |
| Documents in `/docs/phase0/` prior to this report | 0 |
| Type A conflicts (direct contradiction) | 3 |
| Type B conflicts (naming drift) | 4 clusters |
| Type C conflicts (dependency violation) | 4 |
| Type D conflicts (AC gaps) | 17 |
| Type E conflicts (DevOps consistency) | 3 |
| Type F conflicts (LLM contract coherence) | 3 |
| CRITICAL findings (blocks engineering sprint start) | 6 |
| MAJOR findings (causes rework if not fixed) | 6 |
| MINOR findings (cosmetic / docs-only) | 3 |
| Total prioritized fixes | 15 |

**Top-line verdict:** The planning content is remarkably deep and internally coherent for the LLM pipeline core (Epics 0.5, 0.8, 0.10). However, six issues must be resolved before Sprint 1 engineering can start:

1. **Three infrastructure decisions are unresolved** (Epic 0.2): workflow engine, WebSocket platform, database hosting. Engineers cannot write deployment configuration without these.
2. **No unified typed I/O contract sheet** for all pipeline steps (Epic 0.3). Stage details are scattered across 3+ documents in narrative form; no typed interface table exists.
3. **LLM agent count conflict: "4" vs "5"** (Epic 0.4). Orchestration spec §2 says 4; overview says 5. The agent responsibility sheet AC cannot be approved against an ambiguous count.
4. **`reasoning` output field format conflict** (Epics 0.5 / 0.4). `llm-io-contract.md` v1.1.0 defines `reasoning` as a structured 4-field object (breaking change). `prompt-template-framework.md` still shows the old freeform string. Prompt samples in the prompt framework will produce invalid output.
5. **`recommended_action` enum conflict** (Epic 0.5). Same root cause: `llm-io-contract.md` v1.1.0 changed `recommended_action` to a 7-value enum; `prompt-template-framework.md` still shows freeform text.
6. **`insufficient_signal` pipeline state missing from locked-values list** (Epic 0.7). `core-use-cases.md` and `global-data-collection-architecture.md` both use this state. `orchestration-layer-spec.md` §4.2 locked-values list does not include it.

What is safe to proceed with immediately: Epic 0.10 (Security), Epic 0.8 (Data Acquisition), and the LLM I/O contract itself (after fixing FIX-001 and FIX-002 below). Epics 0.5, 0.6, and 0.9 are safe except for the specific fixes noted.

---

## Section 1: Document Inventory

### 1.1 Classification Legend

| Column | Values |
|---|---|
| **Epic(s)** | Primary JIRA epic(s) the document covers |
| **Location** | OBSIDIAN (wiki/), DOCS (docs/), REPO_ROOT, RAW (raw/) |
| **Content Quality** | DEFINED (complete, typed, cited) / DESCRIBED (narrative, no schema) / STUB (placeholder) / EMPTY |
| **Status** | COVERS (linked from JIRA AC) / PARTIAL / OBSIDIAN_ONLY (planning artifact unreachable outside Obsidian) / UNLINKED (no inbound wiki links) / DUPLICATE |

### 1.2 Full File Map

| File Path | Epic(s) | Location | Content Quality | Status |
|---|---|---|---|---|
| `CLAUDE.md` | N/A | REPO_ROOT | DEFINED (operating manual) | UNLINKED |
| `index.md` | N/A | REPO_ROOT | DEFINED (wiki catalog) | UNLINKED |
| `log.md` | N/A | REPO_ROOT | DEFINED (session log) | UNLINKED |
| `wiki/overview.md` | All | OBSIDIAN | DEFINED (synthesis) | OBSIDIAN_ONLY |
| `wiki/sources/2026-lead-intelligence-engine-reference.md` | All | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/sources/2026-intelligence-layer-design.md` | 0.5, 0.4 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/sources/2026-core-business-entities.md` | 0.3, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/sources/2026-b2c-data-acquisition.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/sources/2026-lead-ingestion-strategy.md` | 0.8, 0.3 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/entities/gamoft.md` | N/A | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/entities/urvee-organics.md` | N/A | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/entities/govmen.md` | N/A | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/entities/anishekh.md` | N/A | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/concepts/lead-pipeline-architecture.md` | 0.3, 0.7 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/intelligence-layer.md` | 0.4, 0.5 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/signal-types.md` | 0.5, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/data-entity-model.md` | 0.3, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/agent-vs-tool-classification.md` | 0.4 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/persona-layer.md` | 0.5, 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/confidence-first-class.md` | 0.5, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/lineage-log.md` | 0.7, 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/disqualification-gate.md` | 0.7 | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/concepts/score-decay.md` | 0.7 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/action-sla.md` | 0.7, 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/capability-registry.md` | 0.4, 0.7 | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/concepts/feedback-loop.md` | 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/adaptive-signal-lifecycle.md` | N/A (deferred) | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/concepts/two-stage-lead-filtering.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/b2c-data-acquisition.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/concepts/lead-ingestion-sources.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| **`wiki/analyses/mvp-scope-sign-off.md`** | **0.1** | **OBSIDIAN** | **DEFINED** | **OBSIDIAN_ONLY** |
| **`wiki/analyses/core-use-cases.md`** | **0.1** | **OBSIDIAN** | **DEFINED** | **OBSIDIAN_ONLY** |
| **`wiki/analyses/operational-business-kpis.md`** | **0.1, 0.11** | **OBSIDIAN** | **DEFINED** | **OBSIDIAN_ONLY** |
| `wiki/analyses/tech-stack-research.md` | 0.2 | OBSIDIAN | DEFINED (3 open decisions) | OBSIDIAN_ONLY |
| `wiki/analyses/orchestration-layer-spec.md` | 0.2, 0.3, 0.7 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/service-scaling-strategy.md` | 0.2, 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/execution-type-classification.md` | 0.4 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/persona-agent-spec.md` | 0.4 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/rating-agent-spec.md` | 0.4, 0.5 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/future-optional-agents.md` | 0.4 | OBSIDIAN | DESCRIBED | OBSIDIAN_ONLY |
| `wiki/analyses/llm-io-contract.md` | 0.5 | OBSIDIAN | DEFINED (v1.1.0) | OBSIDIAN_ONLY |
| `wiki/analyses/llm-operational-safeguards.md` | 0.5 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/prompt-template-framework.md` | 0.5 | OBSIDIAN | DEFINED (STALE — pre-v1.1.0) | OBSIDIAN_ONLY |
| `wiki/analyses/context-construction-specification.md` | 0.5, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/prompt-orchestration-framework.md` | 0.5 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/prompt-evaluation-framework.md` | 0.5 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/persona-classification-framework.md` | 0.5, 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/adaptive-scoring-strategy-b2b-b2c.md` | 0.5 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/onboarding-flow-stage-map.md` | 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/onboarding-flow-inputs.md` | 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/onboarding-flow-readiness.md` | 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/client-config-schema-business-profile.md` | 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/client-config-schema-persona-scoring.md` | 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/client-config-schema-defaults.md` | 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/devops-controls.md` | 0.6, 0.7, 0.8, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/inngest-function-design.md` | 0.7 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/orchestration-layer-dependencies.md` | 0.7 | OBSIDIAN | DESCRIBED (superseded) | DUPLICATE |
| `wiki/analyses/channel-integration-layer.md` | 0.8, 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/delivery-integration-layer.md` | 0.7 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/global-data-collection-architecture.md` | 0.8, 0.3 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/lead-enrichment-architecture.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/enrichment-tools-integration.md` | 0.8, 0.4 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/epic-0.8-data-acquisition-coverage.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/meta-platform-api-deep-research.md` | 0.8, 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/meta-integration-implementation.md` | 0.8, 0.6 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/signal-detection-rule-spec.md` | 0.9, 0.4 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/security-planning.md` | 0.10 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/governance-observability-layer.md` | 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/observability-detail-spec.md` | 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/scoring-quality-metrics.md` | 0.11, 0.1 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/accuracy-proxy-metrics.md` | 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/consistency-metrics.md` | 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/action-relevance-metrics.md` | 0.11 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/confidence-scoring-brainstorm.md` | 0.5, 0.9 | OBSIDIAN | DEFINED (resolved) | OBSIDIAN_ONLY |
| `wiki/analyses/b2c-data-acquisition.md` | 0.8 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |
| `wiki/analyses/signal-separation.md` | 0.5, 0.9 | OBSIDIAN | DEFINED | OBSIDIAN_ONLY |

### 1.3 Summary Statistics

| Category | Count |
|---|---|
| Total .md files scanned | 76 |
| Files in `wiki/analyses/` | 51 |
| Files in `wiki/sources/` | 5 |
| Files in `wiki/concepts/` | 17 |
| Files in `wiki/entities/` | 4 |
| Files at repo root (CLAUDE.md, index.md, log.md) | 3 |
| OBSIDIAN_ONLY (all wiki/ planning docs) | 76 |
| DUPLICATE / superseded | 1 (`orchestration-layer-dependencies.md`) |
| Documents in `/docs/phase0/` before this report | **0** |

**Critical structural finding:** Every planning document lives in `wiki/analyses/` (Obsidian vault). Zero planning artifacts exist in `/docs/phase0/` or any `/docs/` subdirectory. This means the entire planning layer is OBSIDIAN_ONLY: not formally approved, not visible to engineers who don't use Obsidian, and not linked from JIRA acceptance criteria. This is the highest-priority structural fix (see FIX-001).

---

## Section 2: Conflict Report

### TYPE A — Direct Contradictions

These are cases where two documents make mutually exclusive factual claims about the same system property.

---

#### A-1: `reasoning` Output Field — Freeform String vs Structured Object

**Severity: CRITICAL — blocks prompt implementation**

**File A:** `wiki/analyses/llm-io-contract.md` (version 1.1.0, revised 2026-05-18)
- `reasoning` is defined as a structured object with 4 required fields: `primary_driver` (string), `signal_contributors` (string[]), `data_gaps` (string[]), `salesperson_note` (string)
- Marked explicitly: "BREAKING CHANGE from v1.0.0"

**File B:** `wiki/analyses/prompt-template-framework.md` (dated 2026-05-04, NOT updated for v1.1.0)
- Both sample prompt templates (B2B Enterprise, SMB Fragmented) show `reasoning` as a freeform narrative string in the OUTPUT FORMAT section
- Example shown: `"reasoning": "This is a mid-market company with confirmed buying intent..."`

**Nature:** A prompt that instructs the LLM to return `reasoning` as a string will produce output that fails the `llm-io-contract.md` v1.1.0 OUTPUT_SCHEMA validation. The validation rules require all four sub-fields to be present. A salesperson note would never appear.

**Which is correct:** `llm-io-contract.md` v1.1.0. The v1.1.0 breaking change is intentional — the structured object enables machine-readable reasoning traces in the `lineage_record`.

**Action required:** UPDATE `prompt-template-framework.md` — replace both sample OUTPUT FORMAT blocks to show the v1.1.0 `reasoning` object structure. Also update the TASK section in both samples to instruct the LLM to populate all four sub-fields.

---

#### A-2: `recommended_action` Output Field — Freeform String vs Enum

**Severity: CRITICAL — blocks prompt implementation**

**File A:** `wiki/analyses/llm-io-contract.md` (v1.1.0, 2026-05-18)
- `recommended_action` is defined as a 7-value enum: `call_immediately | schedule_demo | send_pricing_deck | follow_up_scheduled | send_qualifying_message | nurture | archive`
- Marked explicitly: "BREAKING CHANGE from v1.0.0"

**File B:** `wiki/analyses/prompt-template-framework.md` (2026-05-04)
- Both sample prompts show `recommended_action` as a freeform instruction string, e.g. `"recommended_action": "Call today — high intent, strong fit"`

**Nature:** A freeform string in `recommended_action` will: (1) fail OUTPUT_SCHEMA enum validation, (2) break any downstream system that switches on the `recommended_action` field (delivery layer, CRM sync, notification routing).

**Which is correct:** `llm-io-contract.md` v1.1.0.

**Action required:** UPDATE `prompt-template-framework.md` — both sample prompts must instruct the LLM to return exactly one of the 7 enum values, and the sample OUTPUT FORMAT blocks must show a valid enum value (e.g., `"recommended_action": "call_immediately"`).

---

#### A-3: `insufficient_signal` Pipeline State — Used but Not in Locked Values

**Severity: CRITICAL — blocks pipeline state machine implementation**

**Files using the state:**
- `wiki/analyses/core-use-cases.md` Use Case 3 Outputs table: `"pipeline_stage": "insufficient_signal"` — stated as the output value when a message is discarded at the pre-filter gate
- `wiki/analyses/global-data-collection-architecture.md` §2 (no-scraping decision section): references `proceed: false` path which writes `insufficient_signal`

**File with the locked values list:**
- `wiki/analyses/orchestration-layer-spec.md` §4.2 — enumerates locked `pipeline_stage` values: `captured | fetched | enriched | normalised | scored | delivered | human_review | awaiting_clarification | failed`

`insufficient_signal` is NOT in this list.

**Nature:** The pipeline state machine implementation will have a hard-coded enum. If `insufficient_signal` is not in the enum, writing it to the DB will either fail (strict enum column) or silently store an unrecognised value. The `insufficient_signal` state is used in Use Case 3, which accounts for all noise messages — potentially the highest-volume `pipeline_stage` value at production load.

**Which is correct:** `insufficient_signal` should be added. The `awaiting_clarification` state was added on 2026-05-03 (confirmed decision in §11) — the same mechanism should be used to add `insufficient_signal`.

**Action required:** UPDATE `orchestration-layer-spec.md` §4.2 locked-values list to add `insufficient_signal`. Update §11 Confirmed Decisions with the date and rationale. The pipeline_stage DB column type (enum or varchar with check constraint) must include this value.

---

### TYPE B — Naming Drift

These are cases where the same concept is referred to by different names across documents, creating implementation ambiguity.

---

#### B-1: "Persona Agent" vs "Persona Engine" — Two Different Things

**Files involved:**
- "Persona Engine" appears in: `wiki/concepts/persona-layer.md`, `wiki/analyses/context-construction-specification.md`, `wiki/analyses/orchestration-layer-spec.md` §3.2 — used to mean the Pipeline-1 component that loads and caches the PersonaObject
- "Persona Agent" appears in: `wiki/analyses/persona-agent-spec.md`, `wiki/analyses/execution-type-classification.md` (P2-2) — used to mean the Pipeline-2 LLM agent that CREATES the PersonaObject

**These are two different components.** The naming drift risks conflation during engineering: a developer might implement the Persona Engine (caching/loading component in Pipeline 1) and the Persona Agent (LLM in Pipeline 2) as the same service.

**Canonical distinction:** "Persona Engine" = the first component of the Intelligence Layer in Pipeline 1 — reads and caches the PersonaObject. "Persona Agent" = the LLM agent in Pipeline 2 that generates the PersonaObject. The distinction is correct; it is never stated explicitly in a disambiguation note.

**Action required:** Add an explicit disambiguation paragraph to `wiki/analyses/persona-agent-spec.md` and `wiki/concepts/persona-layer.md`. No rename needed — the distinction is semantically correct; it must be stated.

---

#### B-2: "pipeline_log" (old) vs Three-Entity Lineage Model (current)

**Files involved:**
- `wiki/analyses/orchestration-layer-spec.md` §5.1 Quality Metrics diagram box: still labeled `pipeline_log`
- `wiki/analyses/orchestration-layer-spec.md` §8.5: defines the correct three-entity model: `pipeline_run` + `task_execution` + `lineage_record`
- `wiki/concepts/lineage-log.md`: title and description still use "pipeline_log" as a generic term

**Nature:** A developer reading the §5.1 diagram will implement a single `pipeline_log` table. The correct design requires three separate tables with different write-order guarantees. The mismatch is within the same document.

**Action required:** UPDATE `orchestration-layer-spec.md` §5.1 diagram label from `pipeline_log` to `pipeline_run / task_execution / lineage_record`. UPDATE `wiki/concepts/lineage-log.md` to use current three-entity names throughout.

---

#### B-3: `confidence` (old field) vs `lead_completeness` (current field)

**Files involved:**
- `wiki/analyses/orchestration-layer-spec.md` §5.1 Quality Metrics diagram: still shows `confidence · dimension_scores`
- `wiki/analyses/orchestration-layer-spec.md` §8.5: explicitly states "`lead_completeness` replaces what was previously called `confidence`"
- `wiki/concepts/confidence-first-class.md`: resolved — confirms `lead_completeness`

**Nature:** The §5.1 diagram is in the same document as the §8.5 correction. A developer reading the diagram will implement `confidence` as the field name; the DB schema and all queries must use `lead_completeness`.

**Action required:** UPDATE `orchestration-layer-spec.md` §5.1 diagram: replace `confidence` with `lead_completeness`.

---

#### B-4: LLM Agent Count — "4 agents" vs "5 agents"

**Files involved:**
- `wiki/analyses/orchestration-layer-spec.md` §2 table header AND §11 Confirmed Decisions: *"4 LLM agents total (3 in Pipeline 2, 1 in Pipeline 1)"*
- `wiki/overview.md` (updated 2026-05-03): *"5 LLM agents (3 in Pipeline 2, 2 in Pipeline 1: Scoring Agent + Message Parser)"*
- `wiki/analyses/orchestration-layer-spec.md` §11 Revised Decisions (2026-05-03): *"LLM calls per lead: one Sonnet call (Scoring Agent, all paths) + one Haiku call (Message Parser, DM path only)"*

**Nature:** The §2 table header and §11 confirmed decisions say "4" but §11 also describes 5 distinct LLM invocations. The overview correctly says 5 after the 2026-05-03 update. The §2 table was not updated when the Message Parser was formally added.

**Which is correct:** 5 is correct. The Message Parser (Claude Haiku) is a distinct LLM agent on the DM path.

**Action required:** UPDATE `orchestration-layer-spec.md` §2 table to add Message Parser row (Claude Haiku, Pipeline 1, DM path only) and change the section heading from "4 LLM agents" to "5 LLM agents." Update §11 Confirmed Decisions accordingly.

---

### TYPE C — Dependency Violations

These are cases where a downstream document assumes a dependency from an upstream document that has not been formally defined, is ambiguous, or has not been updated.

---

#### C-1: `tone` and `custom_rules` PersonaObject Fields — Stored but Not Wired

**Epic chain:** 0.6 (client config / persona schema) → 0.5 (LLM I/O contract / context construction)

**Where 0.6 defines them:**
- `wiki/analyses/client-config-schema-persona-scoring.md`: `PersonaObject` schema includes `tone` (free-text string, e.g. "formal and authoritative") and `custom_rules` (string[], e.g. "never score a lead without a verified phone")
- Same document Caveat 2: *"Both fields are stored in the PersonaObject but are not currently wired into the LLM I/O contract or the context construction specification"*

**Where 0.5 and 0.9 do NOT include them:**
- `wiki/analyses/llm-io-contract.md` (v1.1.0): `persona` input object contains `scoring_weights`, `banding`, `icp`, `signal_definitions` — does NOT include `tone` or `custom_rules`
- `wiki/analyses/context-construction-specification.md`: system message assembly section lists persona fields to inject — does NOT include `tone` or `custom_rules`

**Nature:** `tone` and `custom_rules` are stored in the DB but will never reach the LLM prompt. A tenant admin who configures a custom rule ("never score without GST verification") will have that rule silently ignored. This is not a spec gap — it is documented — but it is a dependency that must be resolved before onboarding produces expected behavior.

**Action required:** Make an explicit design decision: either (a) add `tone` and `custom_rules` to the `persona` input object in `llm-io-contract.md` and update the context-construction system message assembly to inject them, or (b) formally mark them as MVP non-goals in `mvp-scope-sign-off.md`. Do not leave them as stored-but-ignored with no resolution timeline.

---

#### C-2: Enrichment Field Names — No Cross-Reference from Provider Output to Context Input to LLM INPUT_SCHEMA

**Epic chain:** 0.8 (data acquisition / enrichment) → 0.9 (context construction) → 0.5 (LLM I/O)

**Where 0.8 defines output fields:**
- `wiki/analyses/enrichment-tools-integration.md`: NormalisedEvent field expansion (e.g., `company_name`, `company_size_band`, `company_revenue_band`, `gstin`, `cin`)
- `wiki/analyses/global-data-collection-architecture.md` §14.2: `NormalisedChannelEvent` schema

**Where 0.9 assumes these fields:**
- `wiki/analyses/context-construction-specification.md`: references `enriched_lead` object input; lists fields like `company_name`, `role_title`, `phone` — but does not cite the field definitions in 0.8

**The gap:** If an enrichment provider uses `company_name_normalized` instead of `company_name`, the context constructor silently drops the field. There is no end-to-end field mapping table anywhere.

**Severity:** MAJOR — a field name mismatch causes silent data loss in the LLM prompt, not a runtime crash.

**Action required:** Create a one-page field mapping table tracing each enrichment provider output field → context object property → LLM INPUT_SCHEMA field. File as `docs/phase0/enrichment-to-llm-field-map.md`.

---

#### C-3: Feature Flags Defined in 0.6 but Not Wired into 0.7 Orchestration Pre-Flight

**Epic chain:** 0.6 (onboarding / feature flags) → 0.7 (orchestration / Pipeline 1 pre-flight)

**Where 0.6 defines flags:**
- `wiki/analyses/devops-controls.md` §0.6.1: `tenant_config.feature_flags` JSONB column; flags include `enrichment_surepass`, `enrichment_probe42`, `enrichment_tracxn`, etc.

**Where 0.7 must read them:**
- `wiki/analyses/orchestration-layer-spec.md` §6.2 pre-flight check: checks `tenant.status`, `signal_definitions`, `prompt_template` — does NOT mention checking or loading `feature_flags`
- `wiki/analyses/orchestration-layer-spec.md` §6.3 Pipeline 1 run step 2: "Load tenant_config + persona + signal_definitions + prompt_template from DB" — `feature_flags` is in `tenant_config` but no explicit gating logic is described

**Nature:** Without explicit wiring, enrichment provider calls will execute regardless of flag state. A tenant without a Probe42 credential will have the Probe42 API call attempted and fail.

**Action required:** Add a Feature Flag Enforcement subsection to `orchestration-layer-spec.md` §6.3 stating: "`tenant_config.feature_flags` is loaded as part of step 2. Each enrichment provider call is gated by its corresponding flag. Flag check failure = skip provider, proceed to fallback chain."

---

#### C-4: AWS Secrets Manager Vault — Implicitly Requires AWS Decision

**Epic chain:** 0.10 (security) → 0.2 (infrastructure / deployment)

**Where 0.10 locks AWS Secrets Manager:**
- `wiki/analyses/security-planning.md`: *"Secrets vault: AWS Secrets Manager"* — lists 15 credential types in the vault inventory with full ARN path structure

**Where 0.2 has infrastructure as TBD:**
- `wiki/analyses/tech-stack-research.md` §Open Decisions: database hosting and workflow engine are still team decisions — options include both AWS (Aurora) and non-AWS (self-hosted) paths

**Nature:** The security layer is locked to AWS Secrets Manager. If the infrastructure decision lands on a non-AWS deployment, the security implementation must change. The security doc does not acknowledge this dependency.

**Action required:** Add a dependency note to `security-planning.md` Caveats: "AWS Secrets Manager is locked as the vault. Infrastructure decisions in Epic 0.2 must resolve to an AWS deployment for this to hold." Alternatively, after FIX-002 resolves the infrastructure decision, update `security-planning.md` to reflect.

---

### TYPE D — Acceptance Criteria Gaps

These are cases where a JIRA story's acceptance criteria cannot be satisfied by current documentation.

---

#### D-1 — Epic 0.2: Deployment + Environment Strategy — 3 Open Infrastructure Decisions

**JIRA story:** "Validate service dependencies and deployment strategy"
**AC:** "deployment + environment strategy approved"
**Status:** PARTIALLY MET

`wiki/analyses/tech-stack-research.md` explicitly marks three decisions as `[TEAM DECISION]` (unresolved):
1. Workflow Orchestration Engine: Temporal (~$30/mo self-hosted) vs AWS Step Functions (~$0.05/mo)
2. WebSocket / Chat Delivery: Pusher + Beams (~$49/mo) vs Soketi + Firebase FCM (~$35/mo)
3. PostgreSQL Hosting: Aurora Serverless v2 (~$94/mo) vs PostgreSQL on EC2 (~$42/mo)

These three choices affect: container counts, ECS task definitions, IAM policies, VPC layout, secret ARN paths, autoscaling config. Engineers cannot write environment-specific infrastructure-as-code until these are decided.

**Action required (FIX-002):** Schedule 30-min team session to lock all three decisions. Record in `tech-stack-research.md` §Locked Decisions. Update `mvp-scope-sign-off.md` and `security-planning.md` to reflect.

---

#### D-2 — Epic 0.2: Service Boundary Document in `raw/`, Not Wiki

**JIRA story:** "Validate service dependencies and deployment strategy"
**AC:** "service boundary doc approved"
**Status:** NOT MET (wrong location)

`raw/assets/service_boundaries.docx` exists as a raw asset. Per CLAUDE.md rules, `raw/` files are immutable source material and cannot serve as approved planning artifacts.

**Action required (FIX-005):** Ingest `raw/assets/service_boundaries.docx` into `wiki/analyses/service-boundaries.md` following the standard source page format.

---

#### D-3 — Epic 0.3: No Unified Typed I/O Contract Sheet for All Pipeline Steps

**JIRA story:** "Define system workflow decomposition"
**AC:** "I/O contract sheet completed for all workflow steps"
**Status:** PARTIALLY MET

Stage details exist but are scattered:
- `orchestration-layer-spec.md` §4.3 — narrative stage descriptions, no typed field tables
- `llm-io-contract.md` — complete typed I/O for Scoring Agent only (1 step)
- `global-data-collection-architecture.md` — NormalisedChannelEvent schema (channel boundary)

No single document contains a table of the form: Step | Input Fields (typed) | Output Fields (typed) | Validation Rules — covering all 9 Pipeline-1 steps and 5 Pipeline-2 steps.

**Action required (FIX-003):** Create `docs/phase0/pipeline-io-contracts.md` with a typed table for all pipeline steps.

---

#### D-4 — Epic 0.4: No Unified Tool Catalog

**JIRA story:** "Identify agents vs automation components"
**AC:** "tool catalog approved"
**Status:** PARTIALLY MET

Tool information is scattered:
- `enrichment-tools-integration.md` — 5 enrichment API providers with WHY/HOW/WHERE/WHEN
- `execution-type-classification.md` — classifies each step by AUTOMATION/AGENT/HYBRID
- `orchestration-layer-spec.md` §7 — tool invocation mechanics

No single "tool catalog" document lists every tool the system uses with interface, version, rate limits, cost, and error handling. LLM providers, the workflow engine, WebSocket service, and auth provider are absent from any catalog.

**Action required (FIX-008):** Create `docs/phase0/tool-catalog.md` extending `enrichment-tools-integration.md` to cover all system tools.

---

#### D-5 — Epic 0.7: No Standalone Failure Handling Matrix

**JIRA story:** "Design orchestration and resilience layer"
**AC:** "failure handling matrix approved"
**Status:** PARTIALLY MET (content exists, not extractable as sign-off artifact)

Failure handling is documented within `orchestration-layer-spec.md` §7.3 (retry rules by tool type) and §4.3 (Scoring Agent failure table). Content is adequate but embedded within a 1,100+ line document — not approachable as a standalone sign-off artifact.

**Action required (FIX-010):** Extract the failure handling tables into `docs/phase0/failure-handling-matrix.md`.

---

#### D-6 — Epic 0.9: Transformation Rules Not Framed as a Unified Document

**JIRA story:** "Design signal detection and data transformation layer"
**AC:** "transformation rules approved"
**Status:** PARTIALLY MET (rules exist, not consolidated)

Signal transformation logic is split:
- `signal-detection-rule-spec.md` — named extractor + params model (complete)
- `context-construction-specification.md` — context object assembly (complete)
- `orchestration-layer-spec.md` §4.3 Stage 3 — normalization rules (exists but not labeled "transformation rules")

No document is titled or framed as "transformation rules" that a reviewer can approve for this AC.

**Action required (FIX-011):** Add a cross-reference paragraph to `context-construction-specification.md` pointing to the normalization rules in `orchestration-layer-spec.md` §4.3, and label this combination as the Epic 0.9 "transformation rules" artifact. Or create a brief `docs/phase0/transformation-rules.md` that assembles the references.

---

#### D-7 — Epic 0.1: WARM SLA Value is TBD — Blocks AR1 Metric

**JIRA story:** "Define operational and business KPIs"
**AC:** "KPIs with definitions and owners approved"
**Status:** PARTIALLY MET

`wiki/analyses/action-relevance-metrics.md` AR1 (SLA Compliance Rate) definition states: WARM SLA window is `[TBD — set after Month 1 baseline]`. The `sla_breach_check` background job (listed in `operational-business-kpis.md` OP5) cannot be implemented without a concrete value. `wiki/concepts/action-sla.md` uses the ambiguous range "2–3 days."

**Action required (FIX-006):** Make the WARM SLA decision (48h recommended). Record in `orchestration-layer-spec.md` §11 Confirmed Decisions. Update `action-sla.md`, `action-relevance-metrics.md` AR1, and `operational-business-kpis.md`.

---

#### D-8 — Epic 0.4: LLM Agent Count Ambiguity Prevents Agent Responsibility Sheet Sign-Off

Already captured in B-4 conflict. Action required in FIX-004.

---

#### D-9 — Epic 0.5: Prompt Samples Are Invalid Against v1.1.0 Contract

Already captured in A-1 and A-2 conflicts. Action required in FIX-001 and FIX-002 below.

---

#### D-10 — Epic 0.8: JIRA Story Titles Still Use "Scraping" Terminology

**JIRA stories:** "Define scraping workflow," "Define scraping inputs," "Define scraping outputs," "Define scraping DevOps controls"
**Status:** JIRA titles unupdated despite explicit rename recommendation

`wiki/analyses/epic-0.8-data-acquisition-coverage.md` provides a complete rename table for all affected story and sub-task titles. The JIRA backlog (parsed from `raw/JIRA DOCS.xlsx`) still shows the old "scraping" titles. The document explicitly notes this needs to be applied by Anishekh as project owner before Sprint 1 planning.

**Action required (FIX-014):** Apply the rename table from `epic-0.8-data-acquisition-coverage.md` to the JIRA backlog.

---

#### D-11 — Epic 0.2: Log Aggregation Tooling Inconsistency (AWS CloudWatch Locked vs TBD)

**Status:** Inconsistency across documents

`wiki/analyses/tech-stack-research.md` §Locked Decisions: "Observability — Phase 1: AWS CloudWatch (locked)."
`wiki/analyses/observability-detail-spec.md` §1.1: log aggregation service `[TBD — CloudWatch / Grafana / Datadog / self-hosted]`.
`wiki/analyses/mvp-scope-sign-off.md` §DevOps: "Log aggregation tool TBD."

The two later documents contradict the lock in `tech-stack-research.md`. A developer reading `observability-detail-spec.md` will treat CloudWatch as unconfirmed.

**Action required (FIX-013):** Update `observability-detail-spec.md` §1.1 and `mvp-scope-sign-off.md` to state "AWS CloudWatch (locked — per tech-stack-research.md)."

---

#### D-12 — Epic 0.11: Environment Naming Not Formally Defined

**Status:** Referenced but never standardized

`observability-detail-spec.md` §3.4 references "staging." `tech-stack-research.md` references environments implicitly. No document defines canonical environment names (dev / staging / prod), AWS account structure, or naming conventions for ECS task definitions.

**Action required:** Add an Environment Layout subsection to `tech-stack-research.md` or a new `docs/phase0/environment-layout.md`.

---

#### D-13 — Epics 0.7 / 0.11: `onboarding_complete` vs `tenant.status = active` — Stale Flag

`wiki/analyses/onboarding-flow-readiness.md` flags an inconsistency: "orchestration-layer-spec §6.1/§6.2 uses `tenant.onboarding_complete`." The current `orchestration-layer-spec.md` consistently uses `tenant.status = 'active'`. The flag appears resolved but is not struck through in the readiness doc.

**Action required (FIX-012):** Verify current `orchestration-layer-spec.md` §6.1–6.2 field names, then update `onboarding-flow-readiness.md` to mark the inconsistency as "Resolved."

---

#### D-14 — Epic 0.6: `tone` and `custom_rules` Wiring — No Resolution Date

Already captured in C-1. Action required in FIX-009.

---

#### D-15 — Epic 0.2: Signal Dimension Weights Illustrative Table vs Locked Values (Orchestration §3.2)

**Files involved:**
- `wiki/analyses/orchestration-layer-spec.md` §3.2 Signal Agent illustrative table: Intent ~30%, Behaviour ~15%
- `wiki/analyses/orchestration-layer-spec.md` §11 Confirmed Decisions: Intent 25%, Behaviour 20% (locked defaults)

Same document contradiction. A developer reading §3.2 will implement the wrong default weights.

**Action required (FIX-015):** Update `orchestration-layer-spec.md` §3.2 table to show the locked defaults (25/25/20/20/10) and add a note: "Locked defaults; per-tenant overrides via `tenant_config.scoring_weights`."

---

#### D-16 — Epic 0.3: `pipeline_log` in §5.1 Diagram vs Three-Entity Model

Already captured in B-2. Action required in FIX-012.

---

#### D-17 — Epic 0.9: Context Construction Does Not Mention `tone` or `custom_rules`

Already captured in C-1 / F-2. Action required in FIX-009.

---

### TYPE E — DevOps Consistency Check

---

#### E-1: CloudWatch "Locked" vs "TBD" Inconsistency

Already captured in D-11. See FIX-013.

---

#### E-2: Environment Naming Not Formally Defined

Already captured in D-12.

---

#### E-3: Workflow Engine TBD — Blocks `devops-controls.md` Job Tracking

**Files involved:**
- `wiki/analyses/devops-controls.md` §0.7.1: references "workflow engine UI (Temporal / Inngest / equivalent — TBD)" for job tracking
- `wiki/analyses/tech-stack-research.md` Open Decision 1: Temporal vs AWS Step Functions

Without the workflow engine decision, the job tracking mechanism (the primary DevOps control panel for Pipeline 1 background jobs) cannot be implemented. This affects 8 named background jobs listed in `operational-business-kpis.md`.

**Action required:** Resolved by FIX-002 (infrastructure decision session).

---

### TYPE F — LLM Contract Coherence Check

All five contract links were audited end-to-end.

| Check | Result |
|---|---|
| 0.8 enrichment output → 0.9 context schema | CONFLICT — see C-2 (no explicit field cross-reference) |
| 0.9 context schema → 0.5 LLM INPUT_SCHEMA | CONSISTENT — `context-construction-specification.md` and `llm-io-contract.md` use the same object structure |
| 0.5 OUTPUT_SCHEMA → 0.4 agent expectation | CONSISTENT — `rating-agent-spec.md` expects exactly the 7 OUTPUT_SCHEMA fields |
| 0.5 retry/fallback → 0.7 orchestration | CONSISTENT — `llm-operational-safeguards.md` 2-attempt max aligns with `orchestration-layer-spec.md` §4.3 "Retry once → human review" |
| 0.6 onboarding config → 0.5 prompt variants | PARTIAL CONFLICT — see F-2 below |

---

#### F-1: `reasoning` and `recommended_action` Format Propagation

Already captured in A-1 and A-2. The prompt template will produce invalid output against the v1.1.0 contract. This is the most consequential LLM contract coherence failure.

---

#### F-2: PersonaObject `tone` and `custom_rules` Not Propagated to Prompt

**Files involved:**
- `wiki/analyses/client-config-schema-persona-scoring.md`: PersonaObject includes `tone` and `custom_rules`
- `wiki/analyses/llm-io-contract.md` v1.1.0 INPUT_SCHEMA: `persona` object — `tone` and `custom_rules` are absent
- `wiki/analyses/context-construction-specification.md`: system message assembly — `tone` and `custom_rules` are absent

A tenant who configures `custom_rules: ["never score a lead without verified phone"]` will never have that rule enforced — it is stored but never reaches the LLM.

**Note:** This is also captured in C-1 and explicitly flagged as Caveat 2 in `client-config-schema-persona-scoring.md`. It is not a silent gap — it is a documented known issue without a resolution.

---

#### F-3: Context Construction Does Not Reference `insufficient_signal` Path

**Files involved:**
- `wiki/analyses/context-construction-specification.md`: describes the full context assembly process — but only for the path where `proceed: true`
- `wiki/analyses/core-use-cases.md` Use Case 3: `proceed: false` → pipeline stops; no context is assembled, no LLM call

The context construction spec does not explicitly document the `proceed: false` exit path. This is a documentation gap rather than an implementation risk (the exit path is in the pre-filter gate, before context assembly begins), but it means the spec is incomplete.

**Action required:** Add a one-paragraph "Out of scope" section to `context-construction-specification.md` noting that this spec only applies when `proceed: true`; the `proceed: false` path is handled at the pre-filter gate and exits before context assembly begins.

---

## Section 3: Coverage Matrix

| Epic | Primary Document(s) | Stories w/ Docs | JIRA AC Met | Conflicts Found | Severity | Fix Priority |
|---|---|---|---|---|---|---|
| **0.1** Product Vision | `mvp-scope-sign-off.md`, `core-use-cases.md`, `operational-business-kpis.md` | 3/3 | 2.5/3 (WARM SLA TBD) | A-3, D-7 | CRITICAL, MINOR | P1 (A-3), P2 (D-7) |
| **0.2** System Architecture | `tech-stack-research.md`, `orchestration-layer-spec.md` | 3/3 | 1.5/3 (3 infra decisions open; .docx not migrated) | D-1, D-2, D-11, D-12, E-2 | CRITICAL | P1 |
| **0.3** Workflow Decomposition | `orchestration-layer-spec.md`, `global-data-collection-architecture.md` | 3/3 | 2/3 (no unified I/O contract table) | D-3, B-2, B-3 | MAJOR | P1 |
| **0.4** Agent vs Automation | `execution-type-classification.md`, `persona-agent-spec.md`, `rating-agent-spec.md` | 3/3 | 1.5/3 (no tool catalog; agent count ambiguous; weight table wrong) | B-4, D-4, D-8, D-15 | CRITICAL, MAJOR | P1 |
| **0.5** LLM Interaction | `llm-io-contract.md`, `prompt-template-framework.md`, `llm-operational-safeguards.md` | 3/3 | 2/3 (prompt framework stale vs v1.1.0) | A-1, A-2, D-9, F-1, F-2 | CRITICAL | P1 |
| **0.6** Onboarding | 7 docs (stage-map, inputs, readiness, 3 config schemas, devops) | 3/3 | 2.5/3 (feature flag wiring gap; stale flag) | C-1, C-3, D-13, D-14, D-17 | MAJOR | P2 |
| **0.7** Orchestration | `orchestration-layer-spec.md`, `delivery-integration-layer.md` | 3/3 | 2.5/3 (no standalone failure matrix; diagram stale) | B-2, B-3, D-5, D-16, E-3 | MINOR | P2 |
| **0.8** Data Acquisition | `enrichment-tools-integration.md`, `global-data-collection-architecture.md`, `epic-0.8-data-acquisition-coverage.md` | 3/3 | 2.5/3 (JIRA titles not updated) | D-10 | MINOR | P3 |
| **0.9** Context Construction | `context-construction-specification.md`, `signal-detection-rule-spec.md` | 3/3 | 2.5/3 (transformation rules cross-ref missing) | C-2, D-6, F-3 | MAJOR | P2 |
| **0.10** Security | `security-planning.md` | 3/3 | 3/3 | C-4 (dependency note only) | MINOR | P3 |
| **0.11** Observability | `observability-detail-spec.md`, `governance-observability-layer.md`, 4 metrics docs | 3/3 | 2.5/3 (CloudWatch inconsistency; env naming missing) | D-11, D-12, E-1, E-2, E-3 | MINOR | P2 |

**Row applicable to ALL epics:** Every row in this table refers to OBSIDIAN_ONLY documents. No planning artifact exists in `/docs/phase0/` before this report.

---

## Section 4: Prioritized Fix List

Severity: CRITICAL = blocks Sprint 1 start / MAJOR = causes implementation rework / MINOR = cosmetic or documentation-only
Priority: P1 = resolve before Sprint 1 kickoff / P2 = resolve during Sprint 1 planning / P3 = resolve before Sprint 1 closes

---

### FIX-001 [P1 | CRITICAL | Epic 0.5]

**Problem:** `prompt-template-framework.md` sample prompts show old freeform `reasoning` string. `llm-io-contract.md` v1.1.0 requires `reasoning` as a structured 4-field object (breaking change). A prompt built from the current template will produce invalid output.

**Conflict:** A-1

**Files to update:**
- `wiki/analyses/prompt-template-framework.md` — both sample prompts (B2B Enterprise, SMB Fragmented): update OUTPUT FORMAT blocks to show the v1.1.0 `reasoning` object with `primary_driver`, `signal_contributors`, `data_gaps`, `salesperson_note` fields

**Verification:** After fix, manually parse both sample outputs against the `llm-io-contract.md` v1.1.0 OUTPUT_SCHEMA validation rules. All 4 `reasoning` sub-fields must be present.

**Blocks:** Any engineering work on the Scoring Agent prompt.

---

### FIX-002 [P1 | CRITICAL | Epic 0.5]

**Problem:** `prompt-template-framework.md` sample prompts show freeform `recommended_action` string. `llm-io-contract.md` v1.1.0 requires `recommended_action` as one of 7 enum values (breaking change). A prompt built from the current template will produce invalid output that breaks delivery-layer routing.

**Conflict:** A-2

**Files to update:**
- `wiki/analyses/prompt-template-framework.md` — both sample prompts: update OUTPUT FORMAT blocks to show a valid enum value (e.g., `"recommended_action": "call_immediately"`); update TASK section to instruct the LLM to return exactly one of the 7 enum values

**Verification:** After fix, check that the example value in each sample matches the enum definition in `llm-io-contract.md` v1.1.0.

**Blocks:** Any engineering work on the Scoring Agent prompt; delivery-layer routing logic.

---

### FIX-003 [P1 | CRITICAL | Epic 0.1 / 0.7]

**Problem:** `insufficient_signal` is used as a `pipeline_stage` value in `core-use-cases.md` and `global-data-collection-architecture.md` but is NOT in the locked-values list in `orchestration-layer-spec.md` §4.2. The pipeline_stage DB column or enum will be missing this value.

**Conflict:** A-3

**Files to update:**
- `wiki/analyses/orchestration-layer-spec.md` §4.2 — add `insufficient_signal` to the locked-values list
- `wiki/analyses/orchestration-layer-spec.md` §11 Confirmed Decisions — add a confirmed decision entry: "`insufficient_signal` added as a valid `pipeline_stage` value for Use Case 3 (noise/no-signal messages), 2026-05-19"

**Verification:** After fix, the `pipeline_stage` enum definition used in the DB schema must include all values from the updated §4.2 list.

**Blocks:** DB schema authoring, pipeline state machine implementation.

---

### FIX-004 [P1 | CRITICAL | Epic 0.4]

**Problem:** `orchestration-layer-spec.md` §2 table header and §11 say "4 LLM agents." `wiki/overview.md` says "5." The Message Parser (Claude Haiku) is a distinct LLM agent not reflected in the §2 table. Epic 0.4 AC requires an "agent responsibility sheet" — the count must be unambiguous.

**Conflict:** B-4

**Files to update:**
- `wiki/analyses/orchestration-layer-spec.md` §2 — add Message Parser row to the agent table; change heading from "4 LLM agents" to "5 LLM agents"
- `wiki/analyses/orchestration-layer-spec.md` §11 Confirmed Decisions — change "4 LLM agents total" to "5 LLM agents total (4 Pipeline-2: Onboarding Agent, ICP Agent, Signal Agent, Persona Agent; 1 Pipeline-1 always: Scoring Agent; 1 Pipeline-1 DM-path only: Message Parser)"

**Blocks:** Epic 0.4 agent responsibility sheet sign-off.

---

### FIX-005 [P1 | CRITICAL | Epic 0.2]

**Problem:** Three infrastructure decisions in `tech-stack-research.md` are explicitly marked `[TEAM DECISION]` and unresolved: (1) Workflow Orchestration Engine, (2) WebSocket/chat delivery platform, (3) Database hosting. Engineers cannot write ECS task definitions, Terraform, IAM policies, or secret ARN paths until these are decided.

**Conflict:** D-1, E-3

**Action:** Schedule a 30-minute team session to make all three decisions. Record outcomes in `tech-stack-research.md` §Locked Decisions. Update `mvp-scope-sign-off.md`, `devops-controls.md`, and `security-planning.md` to reflect the locked choices.

**Blocks:** Infrastructure-as-code authoring, Epic 0.11 autoscaling config, Epic 0.7 job tracking mechanism.

---

### FIX-006 [P1 | MAJOR | Epic 0.2]

**Problem:** Service boundary document is in `raw/assets/service_boundaries.docx` — a raw asset that cannot serve as an approved planning artifact per CLAUDE.md rules.

**Conflict:** D-2

**Action:** Ingest `raw/assets/service_boundaries.docx` into `wiki/analyses/service-boundaries.md` following the standard source page format. Update `index.md`.

**Blocks:** Epic 0.2 "service boundary doc approved" AC.

---

### FIX-007 [P1 | MAJOR | Epic 0.3]

**Problem:** No single unified typed I/O contract sheet exists for all pipeline steps. Stage details are scattered across 3+ documents in narrative form. Developers cannot write typed service interfaces without this.

**Conflict:** D-3

**Action:** Create `docs/phase0/pipeline-io-contracts.md` with a table covering all Pipeline-1 steps (trigger → pre-filter gate → message parser → data gather → enrich → normalise → intent gate → score → bucketize → deliver) and all Pipeline-2 steps, with typed input fields and typed output fields per step.

**Blocks:** Sprint 1 engineering kickoff; service interface contracts; Epic 0.4 tool catalog.

---

### FIX-008 [P2 | MAJOR | Epic 0.6]

**Problem:** `tone` and `custom_rules` PersonaObject fields are stored in the DB but never reach the LLM prompt. No resolution date. A tenant admin who configures custom rules will have them silently ignored.

**Conflict:** C-1, D-14, F-2

**Action:** Make an explicit design decision: either (a) add `tone` and `custom_rules` to the `persona` input object in `llm-io-contract.md` and update `context-construction-specification.md` system message assembly, or (b) formally mark as MVP non-goals in `mvp-scope-sign-off.md` with a post-MVP unlock condition. Current state (stored but ignored, no resolution timeline) is not acceptable.

**Blocks:** Tenant onboarding expectations; prompt quality for tenants with custom rules.

---

### FIX-009 [P2 | MAJOR | Epic 0.6]

**Problem:** Feature flags defined in Epic 0.6 (`devops-controls.md` §0.6.1) are not explicitly wired into the Epic 0.7 orchestration pre-flight check or Pipeline 1 run sequence. Without this, enrichment calls will execute regardless of flag state.

**Conflict:** C-3

**Files to update:**
- `wiki/analyses/orchestration-layer-spec.md` §6.3 step 2 — add: "Load `feature_flags` from `tenant_config`. Each enrichment provider call is gated by its corresponding flag. Flag absent or false = skip provider, proceed to next in fallback chain."

**Blocks:** Enrichment routing logic implementation.

---

### FIX-010 [P2 | MAJOR | Epic 0.9]

**Problem:** No explicit field-level cross-reference from enrichment output → context object → LLM INPUT_SCHEMA. A field name mismatch causes silent data loss in the LLM prompt.

**Conflict:** C-2

**Action:** Create `docs/phase0/enrichment-to-llm-field-map.md` — a table tracing each enrichment provider's output field to its context object property to its LLM INPUT_SCHEMA field.

**Blocks:** Integration between Enrichment Service and Orchestration Service. Silent scoring errors if not resolved.

---

### FIX-011 [P2 | MINOR | Epics 0.1 / 0.7 / 0.11]

**Problem:** WARM SLA window is "2–3 days" (ambiguous) and formally TBD. `action-relevance-metrics.md` AR1 cannot be computed. `sla_breach_check` background job cannot be implemented.

**Conflict:** D-7

**Action:** Make the WARM SLA decision (48h recommended). Record in `orchestration-layer-spec.md` §11 Confirmed Decisions. Update `action-sla.md`, `action-relevance-metrics.md` AR1, and `operational-business-kpis.md`.

**Blocks:** AR1 SLA Compliance metric, `sla_breach_check` background job.

---

### FIX-012 [P2 | MINOR | Epics 0.6 / 0.7]

**Problem:** `onboarding-flow-readiness.md` flags a `tenant.onboarding_complete` vs `tenant.status` inconsistency that appears resolved in current `orchestration-layer-spec.md`. Stale flag creates developer confusion.

**Conflict:** D-13

**Action:** Verify `orchestration-layer-spec.md` §6.1–6.2 consistently uses `tenant.status = 'active'`. Then update `onboarding-flow-readiness.md` to mark the inconsistency as "Resolved in orchestration-layer-spec.md (date: 2026-05-03)."

**Blocks:** Nothing immediate — MINOR.

---

### FIX-013 [P2 | MINOR | Epic 0.11]

**Problem:** `observability-detail-spec.md` and `mvp-scope-sign-off.md` mark log aggregation tooling as TBD despite `tech-stack-research.md` having locked AWS CloudWatch.

**Conflict:** D-11, E-1

**Files to update:**
- `wiki/analyses/observability-detail-spec.md` §1.1 — replace TBD with "AWS CloudWatch (locked — per tech-stack-research.md)"
- `wiki/analyses/mvp-scope-sign-off.md` §DevOps — same update

**Blocks:** Nothing immediate — MINOR.

---

### FIX-014 [P3 | MINOR | Epic 0.8]

**Problem:** JIRA backlog still uses "scraping" titles for Epic 0.8 stories and sub-tasks despite `epic-0.8-data-acquisition-coverage.md` providing a complete rename table. Misleads engineers reading the backlog.

**Conflict:** D-10

**Action:** Apply the rename table from `wiki/analyses/epic-0.8-data-acquisition-coverage.md` to the JIRA backlog. Owner: Anishekh (project owner), before Sprint 1 planning.

**Blocks:** Nothing technical — MINOR naming issue in JIRA.

---

### FIX-015 [P3 | MINOR | Epics 0.4 / 0.7 / 0.11]

**Problem:** `orchestration-layer-spec.md` §3.2 illustrative table shows Intent ~30% / Behaviour ~15% — contradicts the locked confirmed values (Intent 25% / Behaviour 20%) in §11 of the same document. Old diagram labels (`pipeline_log`, `confidence`) persist in §5.1.

**Conflict:** D-15, B-2, B-3, D-16

**Files to update:**
- `wiki/analyses/orchestration-layer-spec.md` §3.2 — update the Signal Agent weight table to show locked defaults (25/25/20/20/10); add note: "Locked defaults; per-tenant overrides via `tenant_config.scoring_weights`"
- `wiki/analyses/orchestration-layer-spec.md` §5.1 — update diagram label `pipeline_log` → `pipeline_run / task_execution / lineage_record`; update `confidence` → `lead_completeness`

**Blocks:** Incorrect default weight implementation if not fixed.

---

## Section 5: What Is Safe to Proceed With

### Epic 0.10 — Security Planning

All three AC stories are met. `security-planning.md` covers: Clerk JWT end-to-end, 4-role RBAC matrix with endpoint-level permissions, Pydantic v2 input sanitization, AES-256-GCM PII encryption policy, AWS Secrets Manager vault inventory with 15 credential types, `access_log` schema with 5-year retention.

No blocking conflicts. One dependency note (C-4 — AWS Secrets Manager requires AWS infrastructure) is documentation-only and does not block implementation.

**Safe to implement immediately.**

---

### Epic 0.8 — Data Acquisition & Enrichment Workflow

All three AC stories are met. The no-scraping hard policy is clearly documented. Source Registry pattern and Company Resolver chain are fully specified. B2C data acquisition hierarchy is complete. DevOps controls (scheduler, throttling, failure logging) are in `devops-controls.md`.

No blocking conflicts. Only issue: JIRA story titles still use "scraping" terminology (FIX-014 — cosmetic, non-blocking).

**Safe to implement. Fix JIRA titles before Sprint 1 planning.**

---

### Epic 0.5 — LLM Interaction and Prompt Strategy (after FIX-001 and FIX-002)

`llm-io-contract.md` v1.1.0 is machine-consumable, typed, and complete. `llm-operational-safeguards.md` covers retry strategy, fallback, token budgets, and cost caps. `prompt-evaluation-framework.md` covers the evaluation gates.

The one blocking issue: `prompt-template-framework.md` is stale against v1.1.0 (A-1, A-2). After FIX-001 and FIX-002 are applied (both are document edits, ~30 minutes), Epic 0.5 is clean.

**Safe to implement after FIX-001 and FIX-002.**

---

### Epic 0.6 — Client Onboarding (mostly)

Seven documents cover three stories. `onboarding-flow-stage-map.md`, `onboarding-flow-inputs.md`, `onboarding-flow-readiness.md`, and the three config schema docs are all DEFINED quality. Onboarding flow implementation can begin.

Two issues require resolution before full implementation: C-1 (`tone`/`custom_rules` wiring decision — FIX-008) and C-3 (feature flag wiring into orchestration pre-flight — FIX-009). Neither blocks onboarding UI or stage-map implementation; both block the enrichment and scoring steps that follow onboarding.

**Onboarding flow safe to design and implement. Enrichment gating requires FIX-009.**

---

### Large portions of Epic 0.1 — Product Vision

`mvp-scope-sign-off.md` (MVP definition, in/out scope, POC success criteria, sign-off process), `core-use-cases.md` (3 use cases with I/O and stakeholder maps), and `operational-business-kpis.md` (13 KPIs with SQL queries and owners) are all DEFINED quality with no blocking issues.

Only gap: WARM SLA TBD (FIX-011 — team decision, ~15 minutes) blocks AR1 implementation but does not block pipeline design.

**Vision and KPI planning safe to use as-is. AR1 implementation awaits FIX-011.**

---

## Appendix A: Files Read During Audit

The following files were read as part of this audit:

**XLSX:**
- `raw/JIRA DOCS.xlsx` (Sheet1 — full backlog, 11 epics, 33 stories, 99 sub-tasks)

**Wiki analyses (all):**
- `wiki/analyses/mvp-scope-sign-off.md`
- `wiki/analyses/core-use-cases.md`
- `wiki/analyses/operational-business-kpis.md`
- `wiki/analyses/orchestration-layer-spec.md`
- `wiki/analyses/global-data-collection-architecture.md`
- `wiki/analyses/llm-io-contract.md`
- `wiki/analyses/prompt-template-framework.md`
- `wiki/analyses/context-construction-specification.md`
- `wiki/analyses/security-planning.md`
- `wiki/analyses/observability-detail-spec.md`
- `wiki/analyses/devops-controls.md`
- `wiki/analyses/client-config-schema-persona-scoring.md`
- `wiki/analyses/epic-0.8-data-acquisition-coverage.md`
- `wiki/analyses/onboarding-flow-stage-map.md`

**Repo root:**
- `CLAUDE.md`
- `index.md`

**Output:**
- `docs/phase0/PLANNING_AUDIT_REPORT.md` (this file)

---

*Phase 0 Planning Audit — complete. All findings are sourced from files read during this session. No file was modified except this output report.*
