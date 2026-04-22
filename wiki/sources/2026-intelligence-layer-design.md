---
type: source
title: "Lead Scoring Agent — Intelligence Layer Design Document"
source_file: raw/assets/intelligence_layer_design.docx
date_ingested: 2026-04-22
tags: [intelligence-layer, design-spec, scoring, persona, prompt, llm, architecture]
---

# Lead Scoring Agent — Intelligence Layer Design Document

**Source:** raw/assets/intelligence_layer_design.docx
**Ingested:** 2026-04-22
**Type:** article (design specification — intended design for build phase)

## Summary

This document is the high-level technical design for the Intelligence Layer of the Lead Scoring system — one of three system layers, alongside the Data Layer and the Orchestration Layer. It defines the layer's single responsibility: take an enriched lead record and a tenant's scoring configuration, and produce a validated scoring output (score 0–100, bucket, one-line reasoning, sub-scores).

The Intelligence Layer contains four components arranged as an internal pipeline: Persona Engine → Prompt Layer → Rating Agent → Output Schema Layer. The sole public interface is `score_lead()`, called by the Orchestration Layer. The layer never writes to the data layer directly — all writes are returned to orchestration. Target scale: 4–5 clients, 50–60 leads/day per client (~300 leads/day total).

The document also provides a detailed walkthrough of how the LLM actually produces a score: the five scoring dimensions (Fit, Intent, Engagement, Behaviour, Context), how the system prompt encodes the rubric, how each enriched lead field maps to a scoring dimension, and how the scoring pipeline connects enrichment → persona → prompt → rating → output.

**Correction noted (2026-04-22):** The design doc uses the term "confidence" for the LLM's self-assessed certainty output. The team has decided this field is **not a confidence score** — it is a **lead completeness score** instead. All references to confidence as an LLM-output field should be read as lead completeness score. The routing logic (needs_review flag, threshold gate) still applies, but the input is completeness of lead data, not LLM self-assessed confidence. See [[concepts/confidence-first-class]] for full correction.

## Key Claims

- The Intelligence Layer is the **only layer that performs LLM-based reasoning**. Isolating it means prompts, model choices, and scoring logic can evolve independently of storage and pipeline triggering.
- **Single LLM call per lead** — the Rating Agent makes exactly one logical model call. Prompt assembly and output validation do not themselves call the LLM.
- **Tenant-aware by configuration, not by code.** Same pipeline serves every client. Differences in behaviour come from the persona object, never from branching logic.
- **Deterministic contracts, non-deterministic core.** The Output Schema Layer guarantees the rest of the system always sees a typed result, even though the LLM output is non-deterministic.
- **Fail loudly, degrade gracefully.** Every component has an explicit failure mode. A failed scoring call returns a typed ScoringFailure, never a silent corruption.
- The Intelligence Layer **does not write directly to the data layer.** The ScoringOutput or ScoringFailure is returned to orchestration, which persists it.
- **Persona versioning confirmed:** the persona object version must be attached to every score record so historical scores can be explained against the config that produced them.
- The intelligence layer's `score_lead()` has a **60-second hard timeout** within the 90-second end-to-end budget.
- The **five scoring dimensions and their default weights:** Fit 25%, Intent 25%, Engagement 20%, Behaviour 20%, Context 10%. Weights are overridden per tenant via the persona object.
- **Banding rules always win over the LLM's own bucket assignment.** When the LLM's bucket disagrees with the banding-rule-derived bucket, banding wins and the discrepancy is logged.
- **Prompt templates are versioned.** Every scoring record stores the prompt version used, enabling rollback and audit.
- The system prompt (rubric) is kept in the system message, not the user message, so it can be cached at the LLM-provider level — reducing token cost.

## Entities Mentioned

- [[entities/gamoft]] — B2B self-tenant; used as the example tenant throughout component specifications
- Groq — mentioned as potential primary LLM provider (speed); open decision not yet locked
- OpenAI — mentioned as potential fallback or primary provider (reliability); open decision not yet locked

## Concepts Mentioned

- [[concepts/intelligence-layer]] — the full 4-component layer defined by this document
- [[concepts/signal-types]] — the five scoring dimensions (Fit, Intent, Engagement, Behaviour, Context) and their default weights
- [[concepts/persona-layer]] — Persona Engine is the first component; builds and caches the PersonaObject from tenant config
- [[concepts/confidence-first-class]] — **corrected**: the design doc's "confidence" field is a lead completeness score in practice, not LLM self-assessed confidence
- [[concepts/lead-pipeline-architecture]] — this document defines the intelligence layer internals; the two-pipeline architecture is the containing context
- [[concepts/lineage-log]] — observability signals emitted by the intelligence layer feed into the governance lineage system

## Questions Raised

- **Primary LLM provider:** Groq (speed) vs OpenAI (reliability) as primary, or Groq primary with OpenAI fallback? Affects latency budget.
- **Model config scope:** Global (one model for all tenants) or per-tenant override capability?
- **Prompt storage:** In code (git-versioned, simpler at current scale) or in data layer (editable without deployment)?
- **Custom rules format:** Free-text rules interpreted by the LLM, or structured rules executed pre-LLM before the model call?
- **Bucket disagreement handling:** When the LLM's bucket and the banding-rule bucket disagree, log only or surface as a dashboard alert?
- **Lead completeness threshold:** What is the threshold below which `needs_review` is set to true? (The doc suggested 0.6 or 0.75 for confidence; this question transfers to completeness threshold.)
- **Are sub-scores required** or can the LLM omit them when lead data is thin?
- **Prompt storage:** Code is simpler at current scale; database is more flexible later. Decision not yet locked.

## Quotes

> "The intelligence layer is the only layer that performs LLM-based reasoning. Isolating it means LLM prompts, model choices, and scoring logic can evolve independently of how data is stored or how pipelines are triggered. A prompt change should never require a database migration; a new data source should never require rewriting the scoring agent."

> "Your competitive advantage isn't the LLM. Anyone can call an LLM. The value you're building is the quality of the system prompt — how well you've captured what 'high intent' looks like across industries, how well you've made the rubric portable across tenants, how well you handle edge cases."

> "If a client says 'you're rating engagement too high', you don't retrain anything. You just lower the engagement weight in that client's persona from 25 to 15, and the prompt layer picks up the change on the next scoring call. Same LLM, same pipeline, different behaviour — because the persona changed."

> "The signals you want the LLM to evaluate must be present in the EnrichedLead. If enrichment doesn't produce a signal, the LLM can't use it — no matter how good the prompt is."
