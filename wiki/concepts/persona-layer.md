---
type: concept
name: "Persona Layer"
aliases: ["Add-on 2", "tenant persona", "personas table", "PersonaObject", "persona engine"]
tags: [multi-tenant, persona, scoring, add-on-2, competitive-moat]
source_count: 2
last_updated: 2026-04-22
---

# Persona Layer

## Definition

A rich per-tenant business profile stored in the `personas` table. Loaded at Phase 00 alongside tenant config and injected into Agent E's prompt at Phase 04. It is what makes the LLM's scoring judgment **tenant-aware** rather than generic. Add-on 2 of v2.0, locked.

The key insight: **same lead → different score across tenants is by design, not a bug.** A director-level lead at a small company might score WARM for Gamoft (B2B, values authority and company size) and COLD for Urvee Organics (B2C, irrelevant profile type).

## Persona Schema `[LOCKED fields, TBD values]`

```json
{
  "tenant_id": "gamoft_001",
  "business_type": "B2B | B2C | Hybrid",
  "industry": "string",
  "target_roles": ["CTO", "Director", "Procurement Head"],
  "company_size_preference": ["SME", "Enterprise"],
  "geography_focus": ["India", "EU"],
  "sales_cycle": "Short | Medium | Long",
  "ticket_size": "Low | Medium | High",
  "decision_complexity": "Single | Multi-stakeholder",
  "priority_signals": ["intent", "authority", "budget"],
  "negative_signals": ["student", "job seeker"]
}
```

## Why It Matters

Without the persona layer, the system is a generic CRM. The persona layer is called the **competitive moat** in the source document. It is what distinguishes this system from weighted-sum rule-based scoring.

The five scoring dimensions (Fit, Intent, Engagement, Behavioral, Context) are weighted *per persona* — same signal, different weight, different outcome.

## How Persona Integrates

- **Phase 00:** Persona loaded alongside tenant config
- **Phase 04:** Agent D injects full persona object into prompt
- **Phase 05:** Agent E evaluates lead against persona
- **Phase 06:** `priority_signals` and `negative_signals` influence bucketing nuance

## Per-Tenant Status

| Tenant | Business Type | Persona Status |
|--------|--------------|----------------|
| [[entities/urvee-organics]] | B2C `[LOCKED]` | `[TBD]` — requires tenant interview |
| [[entities/gamoft]] | B2B `[LOCKED]` | `[TBD]` — internal discussion needed |
| [[entities/govmen]] | `[TBD]` | `[TBD]` — entirely unknown |

## Evidence & Examples

- Example difference: "Requested pricing twice in 48h" signals HOT intent for Gamoft B2B. For Urvee B2C the same signal may indicate a casual comparison shopper. Persona context changes the interpretation. (source: [[sources/2026-lead-intelligence-engine-reference]])
- `priority_signals` and `negative_signals` in the persona schema directly shape disqualification rules in the [[concepts/disqualification-gate]]. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None yet. Persona definitions themselves are `[TBD]` for all three tenants — when populated, real tensions between scoring assumptions may surface.

## Persona Engine (Intelligence Layer Component)

The **Persona Engine** is the first component of the [[concepts/intelligence-layer]]. It builds the PersonaObject from the stored tenant configuration and supplies it to the Prompt Layer. Key behaviours:

- Loads tenant config on demand; caches PersonaObjects in memory with a **15-minute TTL**.
- Cache is invalidated when a tenant updates their scoring rubric.
- Fails fast if required config fields are missing — an incomplete persona is never passed downstream.
- Reads tenant config directly from the Data Layer (the only direct Data Layer read in the Intelligence Layer).

**PersonaObject fields (from intelligence layer design spec):**
```
tenant_id, business_type (B2B/B2C), icp (IcpDefinition),
scoring_weights {fit, intent, engagement, behaviour, context},
banding {hot_min, warm_min, cold_max},
custom_rules (list), tone, version
```

The `scoring_weights` field in PersonaObject is where per-tenant dimension weight overrides live. See [[concepts/signal-types]] for the five dimensions and their defaults.

**Persona versioning confirmed:** The persona version must be attached to every scoring record so historical scores can be explained against the configuration that produced them. (source: [[sources/2026-intelligence-layer-design]])

## Data Model Backing

The persona layer maps to these data entities (see [[concepts/data-entity-model]]):
- `business_profile` + `business_profile_source` — the raw business understanding
- `ideal_customer_profile` — the inferred target customer definition
- `business_profile_version` + `ideal_customer_profile_version` — versioned snapshots for historical explainability

## Related Concepts

- [[concepts/intelligence-layer]] — Persona Engine is the first of four internal components
- [[concepts/signal-types]] — persona scoring_weights determine per-tenant dimension weights
- [[concepts/agent-vs-tool-classification]] — Persona is why the Scoring Agent needs LLM judgment
- [[concepts/lead-pipeline-architecture]] — persona produced by Onboarding Agent in Pipeline 2; loaded at scoring time in Pipeline 1
- [[concepts/disqualification-gate]] — negative_signals feed disqualification rules
- [[concepts/confidence-first-class]] — persona banding rules determine bucket thresholds used in completeness routing
- [[concepts/data-entity-model]] — business_profile, ideal_customer_profile, and version entities back the persona layer

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 02, 04, 05.3, 09.2, 15, 19.2
- [[sources/2026-intelligence-layer-design]] — Section 3.1 Persona Engine; Section 5 Tenant Model
