---
type: concept
name: "Two-Stage Lead Filtering"
aliases: ["rule filter + LLM classification", "noise filtering", "lead vs noise classification"]
tags: [filtering, whatsapp, instagram, llm-classification, noise, ingestion, phase-0]
source_count: 1
last_updated: 2026-05-16
confidence: high
---

# Two-Stage Lead Filtering

## Definition

The noise-elimination mechanism applied to WhatsApp Business and Instagram DM messages before they are treated as leads. Operates in two sequential stages — rule-based discard first, then LLM classification — applied at the Ingestion Service layer, upstream of Pipeline 1.

## Why It Matters

WhatsApp and Instagram inboxes receive a mix of buyer inquiries, existing customer messages, greetings, spam, and operational notifications. Without filtering, Pipeline 1 would process a high volume of non-leads, wasting LLM cost and degrading scoring quality. The two-stage design minimizes LLM invocations (expensive) while keeping the false-negative rate low (missing a lead is more costly than processing noise).

## Stage 1 — Rule-Based Filter

Applied first. Fast, deterministic, no LLM cost.

**WhatsApp rules (drop if any match):**
- Pure greetings (e.g., "hi", "hello")
- Single-word replies
- Messages from numbers already marked as "not a lead"
- Messages from verified business accounts (likely vendors, not customers)

**Instagram-specific additional rules:**
- Sender account <30 days old
- Sender with very few followers
- Sender flagged as a bot
- Story reactions
- Emoji-only messages

**Estimated elimination rate:** ~30–40% of incoming messages dropped at this stage without any LLM invocation.

## Stage 2 — LLM Classification

Applied to messages that survive Stage 1. Uses a fast, low-cost LLM (Claude Haiku or GPT-4o-mini).

**Input:** Message text + tenant business context + ideal customer profile
**Output labels:**
- `LEAD` — process through Pipeline 1
- `EXISTING_CUSTOMER` — route separately (not a new lead)
- `NOISE` — discard
- `UNCLEAR` — treated as LEAD (calibration rule: default-to-LEAD when uncertain)

**Calibration principle:** "Missing a real lead is more costly than processing some noise." When uncertain, LEAD is the safe default.

## Instagram-Specific Preprocessing

Before Stage 2 classification, Instagram messages go through two additional preprocessing steps not present for WhatsApp:

- **Voice notes:** Transcribed via a speech-to-text service, then passed to Stage 2 as text.
- **Image-only messages:** Logged in Phase 0 but not classified — no visual content analysis in Phase 0. (Phase 1 path for image classification is unspecified.)

## Tenant Feedback Integration

Classified leads that enter Pipeline 1 include a "This is not a lead" option in the tenant dashboard. Tenant rejections feed back into classifier improvement over time. This is a distinct feedback path from the salesperson outcome feedback (thumbs up/down) in the main [[concepts/feedback-loop]] — it targets the ingestion classifier specifically, not the scoring weights.

## Tensions & Contradictions

- The classifier is described as a separate "fast, low-cost LLM" call at the ingestion layer. However, the orchestration layer spec also includes a Message Parser (Haiku) as Step 1 of Pipeline 1 for DM messages. Whether Stage 2 classification and the Message Parser are the same LLM invocation (combined into one step) or two distinct calls is unresolved. If they are separate, the cost model needs to account for two LLM calls on the DM path before scoring. (sources: [[sources/2026-lead-ingestion-strategy]], [[analyses/orchestration-layer-spec]])
- The 30–40% rule-filter elimination rate is an estimate; no calibration data exists yet. The actual rate will depend on tenant-specific inbox composition and may vary significantly between B2B and B2C tenants.

## Related Concepts

- [[concepts/lead-ingestion-sources]] — two-stage filtering is the noise mechanism for the WhatsApp and Instagram ingestion paths
- [[concepts/feedback-loop]] — tenant "not a lead" flag provides classifier-specific feedback distinct from scoring-weight feedback
- [[concepts/lead-pipeline-architecture]] — filtered messages trigger Pipeline 1 runs; this filtering happens upstream of the pipeline

## Sources

- [[sources/2026-lead-ingestion-strategy]] — full specification of both stages, Instagram-specific rules, calibration principle, tenant feedback path
