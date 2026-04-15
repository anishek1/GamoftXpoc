---
type: entity
entity_type: organization
name: "Urvee Organics"
aliases: ["Urvee"]
tags: [tenant, b2c, poc]
source_count: 1
last_updated: 2026-04-14
---

# Urvee Organics

**Type:** organization  
**Also known as:** Urvee  
**Role in this wiki:** B2C tenant in the Lead Intelligence Engine POC

## Summary

Urvee Organics is a B2C tenant in the POC. It appears to sell organic products (reference to "oil categories" in product taxonomy context). It has active presence on Instagram and WhatsApp, making it a representative B2C lead source. Its persona will differ substantially from Gamoft's B2B persona — the same incoming lead signals mean different things for organic consumer sales vs. enterprise software sales.

## Key Facts

- Business type: B2C `[LOCKED]` (source: [[sources/2026-lead-intelligence-engine-reference]])
- Active channels: WhatsApp, Instagram (implied; website also likely) (source: [[sources/2026-lead-intelligence-engine-reference]])
- Product taxonomy: includes oil categories (source: [[sources/2026-lead-intelligence-engine-reference]])
- Full persona `[TBD]` — requires tenant interview (source: [[sources/2026-lead-intelligence-engine-reference]])
- Public verification uses: Instagram profile, Facebook, review history (source: [[sources/2026-lead-intelligence-engine-reference]])

## Appearances

| Source | Context |
|--------|---------|
| [[sources/2026-lead-intelligence-engine-reference]] | B2C POC tenant; example used throughout for B2C scoring behavior |

## Related Entities

- [[entities/gamoft]] — system builder; B2B co-tenant
- [[entities/govmen]] — third co-tenant

## Related Concepts

- [[concepts/persona-layer]] — Urvee's B2C persona needed; priority signals differ from B2B
- [[concepts/disqualification-gate]] — different disqualification rules expected for B2C vs B2B
- [[concepts/lead-pipeline-architecture]] — Agent A fetches from Urvee's channels

## Open Questions

- Full persona definition (requires tenant interview)
- Exact product taxonomy for normalization in Agent C
- Whether order database exists and integration path (e-commerce system)
- CRM integration target for internal history lookup
