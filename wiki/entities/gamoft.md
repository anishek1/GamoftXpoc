---
type: entity
entity_type: organization
name: "Gamoft"
aliases: []
tags: [tenant, b2b, poc, builder]
source_count: 1
last_updated: 2026-04-14
---

# Gamoft

**Type:** organization  
**Role in this wiki:** Builder and B2B self-tenant of the Lead Intelligence Engine

## Summary

Gamoft is the organization building the Multi-Tenant Adaptive Lead Intelligence Engine. It occupies a dual role: the engineering team building the system and simultaneously acting as one of the three POC tenants (B2B self-tenant). Anishekh ([[entities/anishekh]]) is the document owner and presumably the lead on this project.

As a B2B self-tenant, Gamoft's full [[concepts/persona-layer]] definition is `[TBD]` — noted as "should be easiest" since they know their own business.

## Key Facts

- B2B business type `[LOCKED]` (source: [[sources/2026-lead-intelligence-engine-reference]])
- Full persona `[TBD]` — requires internal discussion (source: [[sources/2026-lead-intelligence-engine-reference]])
- Assumed AWS hosting `[ASSUMPTION CHECK]` (source: [[sources/2026-lead-intelligence-engine-reference]])
- Backend language under consideration: Laravel (Anishekh's preference from memory) vs Python vs Node `[TBD]`

## Appearances

| Source | Context |
|--------|---------|
| [[sources/2026-lead-intelligence-engine-reference]] | Owner org; B2B self-tenant in POC; system builder |

## Related Entities

- [[entities/anishekh]] — document owner and project lead
- [[entities/urvee-organics]] — co-tenant in POC
- [[entities/govmen]] — co-tenant in POC

## Related Concepts

- [[concepts/persona-layer]] — Gamoft needs its own B2B persona defined
- [[concepts/lead-pipeline-architecture]] — system Gamoft is building

## Open Questions

- Full B2B persona definition for Gamoft as a tenant
- Backend language/framework decision
- Team size and sprint timeline (`[TEAM INPUT]`)
