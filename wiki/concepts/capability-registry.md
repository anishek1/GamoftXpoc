---
type: concept
name: "Capability Registry"
aliases: ["registry pattern", "agent registry", "use-case registry"]
tags: [architecture, extensibility, orchestration]
source_count: 1
last_updated: 2026-04-14
---

# Capability Registry

## Definition

A configuration that maps a **use case** to an **ordered list of agent/tool IDs**. The orchestrator looks up the registry to determine which components to invoke, in what order, for a given task. This makes the orchestrator extensible without code changes.

## Example Mappings

```
lead_enrichment   → [source_fetch, gather, normalise, prompt_build, enrich]
social_growth     → [platform_audit, content_analyse, benchmark, recommend]
```

Adding a new use case = build new components + add one registry entry. **Zero changes to the orchestrator.**

## Anti-Pattern `[LOCKED]`

Do NOT build "auto-generate subagents" capability. Dynamically creating LLM subagents at runtime is not production-ready. The correct approach is a registry of **pre-built, tested agents** that are added manually.

## Storage

`[TBD]` — YAML vs JSON vs DB table, with versioning strategy.

## Why It Matters

The registry is what makes this architecture scalable *for the builder* — not just for the data load. It allows the team to ship new capabilities (social growth analysis, competitive intelligence, etc.) without touching the orchestrator logic.

## Evidence & Examples

- "Adding new use case = (1) build new agents, (2) test in isolation, (3) add one line to registry config. Orchestrator requires ZERO changes." (source: [[sources/2026-lead-intelligence-engine-reference]])
- Anti-pattern reference: manager's ChatGPT suggested dynamic agent creation; rejected in chat. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

None identified.

## Related Concepts

- [[concepts/lead-pipeline-architecture]] — registry lives in Phase 07
- [[concepts/agent-vs-tool-classification]] — registry only references pre-classified components

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 12.1, 19.10
