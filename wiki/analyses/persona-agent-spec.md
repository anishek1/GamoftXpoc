---
type: analysis
question: "What are the inputs, logic, outputs, and invocation conditions for the Persona Agent?"
date: 2026-04-26
tags: [agents, persona-agent, pipeline-2, onboarding, specification, minimal-agent-set]
sources_consulted:
  - "[[concepts/agent-vs-tool-classification]]"
  - "[[concepts/persona-layer]]"
  - "[[concepts/signal-types]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/lead-pipeline-architecture]]"
status: COMPLETE
---

# Persona Agent — Specification

**Role in minimal agent set:** One of two agents in the system. Runs once per tenant at onboarding. Produces the entire scoring intelligence configuration that the Rating Agent uses for every subsequent lead. No lead is ever scored without a Persona Agent output.

---

## Naming Clarification — Persona Agent vs Persona Engine

These are two different components. Confusing them breaks the architecture.

| Name | What it is | When it runs | Type |
|---|---|---|---|
| **Persona Agent** *(this document)* | Pipeline 2 LLM agent that *creates* the tenant's business persona, ICP, and signal definitions from scratch | Once at onboarding; re-runs on business change | HYBRID (LLM Agent) |
| **Persona Engine** | Component 1 of the Intelligence Layer. A *caching and loading* tool — reads the stored output of the Persona Agent and assembles a PersonaObject for each scoring call | Every Pipeline 1 lead score | AUTOMATION (TOOL) |

**Rule:** The Persona Agent writes configuration. The Persona Engine reads it. They never run at the same time.

---

## What the Persona Agent Does

The Persona Agent transforms unstructured tenant knowledge into explicit, structured scoring configuration. It runs as a sequential three-step LLM pipeline. Each step's output is the next step's input. The final output is a complete, self-consistent configuration set that defines how every lead this tenant ever submits will be evaluated.

Without Persona Agent output, Pipeline 1 cannot run. The pre-flight check at every Pipeline 1 run verifies this output exists before touching any leads.

---

## Inputs

### Primary Inputs (always required)

| Input | Type | Source | Notes |
|---|---|---|---|
| `tenant_id` | string | Orchestrator | Identifies the tenant; scopes all output |
| `business_description` | free text | Tenant (via P2-1 intake) | The tenant's own description of their business — strengthened by LLM during intake (see P2-1 in [[analyses/execution-type-classification]]) |
| `business_type` | enum: B2B \| B2C \| Hybrid | Tenant (confirmed at intake) | Locked early; influences which signal dimensions are most relevant |
| `industry` | string | Tenant | Sector context for ICP and signal relevance |
| `target_roles` | list of strings | Tenant | Who the decision-makers and influencers are (B2B); or demographic profile (B2C) |
| `geography_focus` | list | Tenant | Which regions or city tiers are in scope |
| `negative_profiles` | list of strings | Tenant | Explicit exclusions: students, job seekers, resellers, etc. |

### Re-run Inputs (only present on re-run)

| Input | Type | Source | Notes |
|---|---|---|---|
| `rerun_reason` | enum: feedback_driven \| checkin_driven | Governance Layer | Why the re-run was triggered |
| `existing_persona` | PersonaObject | Data Layer (via orchestrator) | The current persona — establishes what is changing vs. what stays the same |
| `detected_pattern` | object | Governance Layer (feedback loop) | Present on feedback_driven re-runs: the pattern that triggered the recommendation |
| `change_description` | free text | Team Lead (from check-in) | Present on checkin_driven re-runs: what the team lead said has changed |
| `team_lead_approval` | boolean, must be true | Team Lead | Re-run cannot start without this. System proposes; human approves. `[LOCKED]` |

---

## Internal Execution — Three Sequential LLM Steps

The Persona Agent is orchestrated as a pipeline of three LLM sub-agents. Each sub-agent makes exactly one logical LLM call.

```
Tenant inputs (+ optional re-run context)
             │
             ▼
   ┌─────────────────────┐
   │   Step 1            │
   │   Business Persona  │
   │   LLM call          │
   │   Input:  raw tenant│
   │           description
   │   Output: Persona   │
   │           Object    │
   └─────────┬───────────┘
             │ PersonaObject
             ▼
   ┌─────────────────────┐
   │   Step 2            │
   │   ICP Definition    │
   │   LLM call          │
   │   Input:  Persona   │
   │           Object    │
   │   Output: ICP       │
   │           Definition│
   └─────────┬───────────┘
             │ PersonaObject + IcpDefinition
             ▼
   ┌─────────────────────┐
   │   Step 3            │
   │   Signal Definition │
   │   LLM call          │
   │   Input:  Persona + │
   │           ICP       │
   │   Output: signal[]  │
   │           (all dims)│
   └─────────┬───────────┘
             │
             ▼
   Orchestrator builds Prompt Template
   (AUTOMATION — not a Persona Agent step)
```

### Step 1 — Business Persona

**LLM task:** Interpret the tenant's business description into a structured PersonaObject.

**Why LLM is needed:** Every tenant's business is described differently. No rule maps "we sell industrial HVAC systems to procurement managers at mid-market factories in tier-1 cities" into a structured persona. The LLM must understand context, infer what matters, and handle gaps gracefully.

**Logic expectations:**
- Infer fields that the tenant did not explicitly provide but that can be reasonably derived from context (e.g., if business_type is B2B and industry is industrial equipment, sales_cycle is likely Medium-Long)
- Flag where inference is uncertain vs. where it is confident — the Persona Agent must not fabricate detail; it should leave fields as unset if there is not enough information
- Apply the tenant's `negative_profiles` to confirm exclusion criteria are internally consistent with their business context
- For re-runs: identify which fields are changing from `existing_persona` and which are stable — change only what the re-run context warrants

**Output — PersonaObject:**

```json
{
  "tenant_id": "string",
  "business_type": "B2B | B2C | Hybrid",
  "industry": "string",
  "target_roles": ["string"],
  "company_size_preference": ["SME", "Enterprise"],
  "geography_focus": ["string"],
  "sales_cycle": "Short | Medium | Long",
  "ticket_size": "Low | Medium | High",
  "decision_complexity": "Single | Multi-stakeholder",
  "product_lines": ["string"],
  "negative_profiles": ["string"],
  "scoring_weights": {
    "fit": 0.25,
    "intent": 0.25,
    "engagement": 0.20,
    "behaviour": 0.20,
    "context": 0.10
  },
  "banding": {
    "hot_min": 80,
    "warm_min": 55,
    "cold_max": 54
  },
  "custom_rules": ["string"],
  "tone": "string",
  "version": "string"
}
```

**Constraint on scoring_weights:** All five dimension weights must sum to 1.0 (100%). The orchestrator validates this after receiving the PersonaObject. If weights do not sum to 1.0, the orchestrator rejects the output and retries with a corrective prompt appended.

**Stored in:** `business_profile` + `business_profile_version` (S1 entities), and as PersonaObject in `personas` table.

---

### Step 2 — ICP Definition

**LLM task:** From the PersonaObject, define who the ideal customer looks like in concrete terms.

**Why LLM is needed:** The PersonaObject defines the *business*. The ICP defines the *ideal buyer*. The relationship requires judgment — what buyer profile optimally matches this business's product, cycle, and economics? This is reasoning, not rule lookup.

**Logic expectations:**
- Define the target segment with enough specificity to be useful (e.g., not just "B2B tech companies" but "Series B–D SaaS companies, 50–500 employees, with a dedicated sales team, looking to scale outbound in India")
- Explicitly list priority signals: which signals should be weighted most heavily for this ICP? These feed into `scoring_weights` refinement if the LLM suggests overrides
- Explicitly list disqualifying signals: what immediately eliminates a lead regardless of other signals? These feed into the Disqualification Gate in Pipeline 1
- List buying triggers: external events that signal a lead is suddenly more likely to convert (fundraise, headcount growth, competitor switch, etc.)
- For re-runs: carry forward ICP elements that have not changed; update only what the change_description or detected_pattern warrants

**Output — IcpDefinition:**

```json
{
  "tenant_id": "string",
  "icp_description": "narrative of the ideal buyer",
  "target_segment": {
    "industry": "string",
    "company_size": "string",
    "geography": "string",
    "role_profile": "string"
  },
  "priority_signals": ["string"],
  "disqualifying_signals": ["string"],
  "buying_triggers": ["string"],
  "icp_examples": ["string"]
}
```

**Stored in:** `ideal_customer_profile` entity (S1) + as `icp: IcpDefinition` embedded inside PersonaObject. Also versioned in `ideal_customer_profile_version`.

**Why embedded AND separate:** The Persona Engine loads the IcpDefinition as part of the PersonaObject at scoring time (embedded = zero extra DB read). The separate `ideal_customer_profile` entity enables historical attribution — when a lead was scored 6 months ago, which ICP definition was active?

---

### Step 3 — Signal Definitions

**LLM task:** From the PersonaObject + IcpDefinition, create the full set of signal definitions the system will use to evaluate every lead this tenant processes.

**Why LLM is needed:** Signals are tenant-specific and domain-specific. The right signals for a B2B HVAC equipment seller (e.g., "procurement approval language", "tender document request") differ entirely from those for a B2C organic products brand (e.g., "repeat purchase indicator", "seasonal intent"). No pre-defined signal set covers all business types. The LLM must reason from business context to signal relevance.

**Logic expectations:**
- Create signals across all five dimensions: Fit, Intent, Engagement, Behaviour, Context
- For each dimension, decide how many signals are needed (Intent: ≥5, Engagement: ≥6, others: sufficient to cover the domain — more signals = richer scoring but longer prompt)
- For each signal: provide a name (machine-readable slug), a description (what it means, what counts as detected), a weight within its dimension (must sum to 1.0 per dimension), and an `applicable_to` tag (B2B | B2C | both)
- For Intent signals especially: think about the *arc of intent progression* — not just individual signals but how the sequence from low to high intent manifests in messages
- The `detection_rule` field is now defined — see [[analyses/signal-detection-rule-spec]]. The Persona Agent outputs a complete detection_rule JSON directly (type + source_fields + params). It is given the extractor vocabulary table in its Step 3 system prompt and must pick a `type` from that table. No engineering mapping step required.
- For re-runs: identify which signals are stable (re-run context did not change the relevant dimension), which need updating, and whether entirely new signals are warranted

**Output — signal[] (one per signal, across all dimensions):**

```json
{
  "signal_id": "uuid",
  "tenant_id": "string",
  "dimension": "fit | intent | engagement | behaviour | context",
  "name": "pricing_request",
  "description": "Lead explicitly asked for a price quote or pricing document",
  "detection_rule": { "type": "keyword_match", "source_fields": ["..."], "params": { "keywords": ["..."] } },
  "weight_within_dim": 0.30,
  "applicable_to": "B2B | B2C | both",
  "version": "string"
}
```

**Stored in:** `signal` table (S1 entity). Per-lead evaluation results stored in `signal_evaluation`.

**After Step 3 completes — Prompt Template Generation (AUTOMATION):**  
The orchestrator reads all signal definitions and generates the prompt template by creating one named slot per signal (`{signal_name}: {value}`). This is not a Persona Agent step — it is deterministic orchestration. The result is stored in `prompt_registry`.

---

## Outputs Summary

| Output | Stored in | Used by |
|---|---|---|
| PersonaObject | `personas` table + `business_profile` | Persona Engine (loads at scoring time), Disqualification Gate (negative_signals) |
| IcpDefinition | `ideal_customer_profile` table (+ embedded in PersonaObject) | Rating Agent (ICP injected into scoring prompt) |
| Signal definitions | `signal` table | Lead Enrichment (signal extraction), Prompt Template Generation, Rating Agent (via prompt template) |
| Prompt template | `prompt_registry` | Rating Agent (via Prompt Layer) |
| Versioned snapshots | `business_profile_version`, `ideal_customer_profile_version` | Governance Layer (historical attribution) |

---

## Invocation Conditions

### When it runs

| Trigger | Condition | Who approves |
|---|---|---|
| New tenant onboarding | First time this tenant_id has no PersonaObject | Automatic (no approval needed — this is setup) |
| Feedback-driven re-run | Governance Layer detects pattern: a signal_version or prompt_version is consistently associated with wrong-bucket leads | Team Lead must approve before re-run starts `[LOCKED]` |
| Check-in-driven re-run | Team Lead indicates significant business change during proactive check-in | Team Lead approval is the trigger itself `[LOCKED]` |

### When it does NOT run

- **Never runs per-lead.** A new lead never triggers the Persona Agent.
- **Never runs automatically.** Re-runs always require explicit team lead approval.
- **Does not run when only minor config changes are needed.** Minor updates (adjusting a signal weight, editing a prompt) go directly to their respective records — no Persona Agent re-run needed. The Persona Agent re-run is for substantive changes to the business persona or ICP.

---

## What the Persona Agent Does NOT Do

| Responsibility | Who owns it |
|---|---|
| Score individual leads | Rating Agent |
| Load or cache the PersonaObject at scoring time | Persona Engine (Intelligence Layer Component 1) |
| Write lineage records | Orchestrator |
| Enforce bucket thresholds | Output Schema Layer (inside Rating Agent call) |
| Apply disqualification rules | Disqualification Gate (Pipeline 1 AUTOMATION step) |
| Trigger its own re-runs | Governance Layer (detects patterns), Team Lead (approves) |
| Build the prompt template | Orchestrator (after Step 3 completes — AUTOMATION) |

---

## Overlap Prevention — Where Persona Agent Ends

The Persona Agent's responsibility ends the moment all three steps are complete and their outputs are stored. From that point:

- The Persona Engine (TOOL, AUTOMATION) owns loading and caching at scoring time
- The Orchestrator owns prompt template generation
- The Rating Agent owns scoring

The only data the Rating Agent ever receives from the Persona Agent is what was persisted in the data layer (PersonaObject, signal definitions, prompt template). The Persona Agent and Rating Agent never communicate directly.

---

## Failure Handling

| Failure | Response |
|---|---|
| Step 1 — PersonaObject weights don't sum to 1.0 | Orchestrator appends correction instruction and retries once |
| Step 1 — Required fields missing in output | 1 retry with explicit field list appended to prompt → if still missing: halt, alert admin, request tenant to provide missing information |
| Step 2 — ICP output too vague to produce actionable signals | Orchestrator flags to admin; team lead manually supplements before Step 3 runs |
| Step 3 — Signal weights within a dimension don't sum to 1.0 | 1 retry with correction → if still failing: halt onboarding |
| Any step — LLM timeout or API failure | 1 retry → if still failing: halt entire Pipeline 2, alert admin |
| Re-run — team_lead_approval missing | Hard stop. Re-run does not start under any condition without explicit approval. |

**On halt:** Pipeline 1 is not blocked by a Persona Agent failure for an existing tenant. Only the affected tenant's onboarding or re-run halts. Existing tenants continue scoring normally.

---

## Open Decisions

| Decision | Status |
|---|---|
| `detection_rule` format (Step 3 signal output) | **RESOLVED 2026-04-28** — named extractor + params. See [[analyses/signal-detection-rule-spec]]. Persona Agent emits directly (no engineering mapping step). |
| Number of signals per dimension | Intent ≥5, Engagement ≥6 confirmed; others TBD per tenant during onboarding |
| Re-run scope: full Pipeline 2 vs ICP+Signal only | Full re-run for persona changes; ICP+Signal-only re-run for feedback-driven patterns `[confirmed in governance spec]` |
| Check-in cadence (triggers re-run proposal) | `[TBD — 2-week or monthly; team decision]` |
| Minimum change threshold to recommend re-run | `[TBD — after Month 1 baseline; team decision]` |

---

## Related Documents

- [[analyses/rating-agent-spec]] — consumes Persona Agent outputs; the other half of the minimal agent set
- [[analyses/future-optional-agents]] — Recommendation Agent and Workflow Agent as future extensions
- [[analyses/execution-type-classification]] — P2-1 through P2-5 execution type breakdown
- [[analyses/orchestration-layer-spec]] — Section 3 (Pipeline 2 flow), Section 6.1 (controller responsibilities)
- [[concepts/persona-layer]] — PersonaObject schema and Persona Engine distinction
- [[concepts/signal-types]] — five scoring dimensions and default weights
- [[concepts/agent-vs-tool-classification]] — agent classification rationale
