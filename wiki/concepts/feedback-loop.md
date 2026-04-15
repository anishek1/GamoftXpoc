---
type: concept
name: "Feedback Loop"
aliases: ["feedback v1", "feedback architecture", "Add-on 6 (deferred)"]
tags: [feedback, learning, scoring, add-on-6-deferred]
source_count: 1
last_updated: 2026-04-14
---

# Feedback Loop

## Definition

The mechanism by which salesperson verdicts on lead outcomes feed back into the scoring system. Two versions: a simple v1 in scope for v2.0, and a three-layer architecture deferred to Sprint 2-3 (Add-on 6).

## v1 (In Scope — v2.0) `[LOCKED]`

- Salesperson marks outcome: **converted / not converted / wrong bucket**
- Reason tags: wrong timing, wrong contact, wrong product, budget
- UX: **ONE TAP** — thumbs up/down per lead card (friction must be minimal)
- Outcomes aggregated weekly per tenant
- Scoring weight adjustments reviewed **monthly** (manual, NOT automated initially)
- Alert: if feedback rate drops below 20%, team lead alerted

**Rule:** "Zero feedback means zero learning." Make it one tap or it won't happen.

## v2 Three-Layer Architecture (Deferred — Add-on 6)

Three feedback loops on different clocks, each fixing a different failure mode:

| Layer | Cadence | What It Fixes |
|-------|---------|---------------|
| 1 — Weight Tuning | Monthly | Wrong scoring weights |
| 2 — Signal Accuracy | Weekly | Wrong signal extraction (Agent B) |
| 3 — Signal Vocabulary | Quarterly | Missing signals entirely |

All three layers read from the same [[concepts/lineage-log]].

**Why deferred:** Adjusting weights fixes nothing when the real error is upstream (bad enrichment, bad normalization, bad prompt, bad LLM judgment). The three-layer fix needs real production data to be meaningful. (source: [[sources/2026-lead-intelligence-engine-reference]])

## Why v1 Feedback Is Often the Wrong Layer

The key insight from Section 19.3: "Original feedback loop attached to wrong layer." Adjusting weights is the last resort. Real failures cascade from:
1. Bad signal extraction
2. Bad enrichment (wrong LinkedIn profile)
3. Bad normalisation
4. Bad prompt template
5. Bad LLM judgment
6. Only THEN: bad weights

v1 only addresses #6. The deferred three-layer system addresses all six.

## Evidence & Examples

- "Make it ONE TAP — thumbs up/down per lead card. If feedback rate drops below 20%, alert team lead. Zero feedback means zero learning." (source: [[sources/2026-lead-intelligence-engine-reference]])

## Tensions & Contradictions

- v1 feedback adjusts weights but cannot diagnose root cause. This is a known limitation, not a contradiction — it's why the deferred architecture is designed the way it is.

## Related Concepts

- [[concepts/lineage-log]] — three-layer system depends on lineage data
- [[concepts/adaptive-signal-lifecycle]] — Add-ons 7/8 work in tandem with Add-on 6
- [[concepts/lead-pipeline-architecture]] — feedback collector is Phase 06 component

## Sources

- [[sources/2026-lead-intelligence-engine-reference]] — Sections 11.6, 17.2, 17.3, 19.3
