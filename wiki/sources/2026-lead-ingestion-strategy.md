---
type: source
title: "Lead Ingestion Strategy"
source_file: raw/assets/Lead_Ingestion_Strategy.docx
date_ingested: 2026-05-16
tags: [ingestion, phase-0, email, whatsapp, instagram, google-sheets, deduplication, filtering, normalization]
---

# Lead Ingestion Strategy

**Source:** [[raw/assets/Lead_Ingestion_Strategy.docx]]
**Ingested:** 2026-05-16
**Type:** note
**Scope:** Phase 0

## Summary

Phase 0 ingests leads from four sources: email, WhatsApp Business, Instagram DMs, and Google Spreadsheet. The first three are push-based (data arrives in real time via webhooks or inbound email); Google Spreadsheet is pull-based (polled every 15 minutes by default, configurable per tenant).

Email ingestion uses a unique per-tenant inbound address (`tenant-{id}@leads.yourplatform.com`). Tenants configure their upstream lead-generation systems to forward notifications to this address. Noise is filtered using subject keyword matching and a sender allowlist. Structural parsing is templated once at onboarding from 2–3 example emails — no per-email LLM call.

WhatsApp Business ingestion requires the WhatsApp Business API (Meta's official platform only — the consumer WhatsApp Business app is not supported). Noise filtering is two-stage: a rule-based stage discards obvious noise (greetings, one-word replies, verified business senders, numbers already marked not-a-lead — roughly 30–40% eliminated without LLM); an LLM classification stage then labels surviving messages as LEAD, EXISTING_CUSTOMER, NOISE, or UNCLEAR, calibrated to default-to-LEAD when uncertain.

Instagram DM ingestion follows the same two-stage filtering model with Instagram-specific additions: sender age, follower count, and bot-flag checks at the rule stage; story reactions and emoji-only messages discarded; voice notes transcribed via speech-to-text before classification; image-only messages logged but not classified in Phase 0.

Google Spreadsheet ingestion uses a service account with read-only access to a specific sheet. Column mapping is done once at setup via LLM-assisted header detection; the tenant confirms or corrects the mapping. A watermark column (timestamp or auto-increment ID) enables efficient delta detection on each poll. No LLM noise filtering — spreadsheets are tenant-curated sources.

Cross-source concerns: all four formats are normalized through adapters into a single internal message structure before downstream processing. Deduplication runs across all sources by matching phone and email — a prospect who contacts the tenant on WhatsApp and also appears in the spreadsheet is treated as one lead with both touchpoints recorded. An immutable intake event log stores every incoming record for replay if filtering rules change or bugs are discovered. Tenants can flag a lead as "not a lead" from the dashboard; this feedback improves classifier performance over time.

## Key Claims

- Phase 0 supports exactly four ingestion sources: email, WhatsApp Business API, Instagram DMs, Google Spreadsheet.
- Email uses unique per-tenant inbound addresses; structural parsing template generated once at onboarding — no per-email LLM call.
- WhatsApp Business API only (not consumer app); two-stage filter; ~30–40% noise dropped at rule stage.
- LLM classifier labels: LEAD, EXISTING_CUSTOMER, NOISE, UNCLEAR; calibration: default-to-LEAD when uncertain.
- Instagram DMs: same two-stage model plus sender profile signals (age, followers, bot flags); story reactions and emoji-only messages discarded at rule stage; voice notes transcribed; image-only logged not classified in Phase 0.
- Google Spreadsheet: service account, 15-min poll (configurable), LLM column mapping once at setup, watermark column for delta detection, no LLM noise filter.
- Deduplication key: phone + email across all four sources; multi-touchpoint leads unified.
- Immutable intake event log enables replay without data loss if rules change.
- Tenant "not a lead" flag feeds classifier improvement over time.
- Normalization adapters convert all four formats to a single internal structure before passing to downstream services.

## Entities Mentioned

- None project-specific beyond existing entities (all platform integrations are third-party services)

## Concepts Mentioned

- [[concepts/lead-ingestion-sources]] — this document is the primary source for the 4-source ingestion design
- [[concepts/two-stage-lead-filtering]] — rule filter + LLM classification; the core noise-filtering mechanism for WhatsApp and Instagram
- [[concepts/feedback-loop]] — tenant "not a lead" flag is a new feedback signal distinct from the salesperson outcome feedback; feeds classifier improvement
- [[concepts/lead-pipeline-architecture]] — these four sources are the triggers that initiate Pipeline 1 (Event/Lead) runs

## Questions Raised

- Which LLM model handles WhatsApp/Instagram classification — is it the same Message Parser (Haiku) already in Pipeline 1, or a separate pre-pipeline classifier? If the same, how does this reconcile with the existing "rule-filter + LLM classification = Stage 1 of Pipeline 1" framing?
- "Not a lead" tenant feedback: how is it stored, and how does it feed back into classifier training? Is this a separate entity from `feedback_record`, or does it use the same governance feedback infrastructure?
- Google Spreadsheet 15-min polling interval: is this configurable in `tenant_config` (alongside other operational limits defined in [[analyses/client-config-schema-defaults]])?
- Voice note transcription for Instagram: which service handles this? Does it go through the LLM cost cap?
- Image-only Instagram messages "logged but not classified in Phase 0" — what entity stores these? Is there a Phase 1 path for visual content classification?
- Immutable intake event log: is this the same as the `lineage_record` entity in the 32-entity catalog, or a separate pre-pipeline store?

## Quotes

> "Missing a real lead is more costly than processing some noise."

> "Google Spreadsheet is a curated source: the tenant maintains the sheet themselves, so every row is intended to be a lead."

> "Every incoming message, email, and row will be stored in an immutable intake event log. This allows us to replay processing if filtering rules change or if a bug is discovered, without losing data."
