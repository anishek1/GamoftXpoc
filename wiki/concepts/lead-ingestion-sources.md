---
type: concept
name: "Lead Ingestion Sources"
aliases: ["ingestion sources", "Phase 0 ingestion", "four-source ingestion"]
tags: [ingestion, phase-0, email, whatsapp, instagram, google-sheets, normalization, deduplication]
source_count: 2
last_updated: 2026-05-16
confidence: high
---

# Lead Ingestion Sources

## Definition

The set of data sources from which leads enter the system in Phase 0, the mechanisms that access each source, and the cross-source concerns (normalization, deduplication, audit, feedback) that make them behave as a unified ingestion layer.

## Phase 0 Sources

| Source | Ingestion Type | Filtering | Access Method |
|---|---|---|---|
| Email | Push (forwarding) | Subject keyword + sender allowlist | Unique per-tenant inbound address |
| WhatsApp Business | Push (webhook) | Rule filter + LLM classification | WhatsApp Business API credentials |
| Instagram DMs | Push (webhook) | Rule filter + LLM classification | Instagram Business OAuth |
| Google Spreadsheet | Pull (15-min poll) | None (tenant-curated) | Service account (read-only) |

## Why It Matters

These four sources are the triggers for every Pipeline 1 run. Nothing reaches the orchestrator, enrichment, or scoring unless it enters through one of these paths. Decisions made here (what is noise, what is a duplicate, what is a real lead) propagate downstream — a missed lead at ingestion is a missed lead permanently.

The source set was chosen to cover the dominant channels B2C and B2B SMB tenants in India (and similar markets) actually receive inquiries on. Google Spreadsheet is included to support tenants who aggregate leads from multiple offline or third-party sources into a manually maintained sheet.

## Email Ingestion Detail

- Each tenant gets a unique inbound address: `tenant-{id}@leads.yourplatform.com`
- Tenant configures upstream systems (web forms, booking tools, contact plugins) to forward notifications to this address
- No access to tenant's primary inbox required
- Filtering: subject keyword match (configured keyword, e.g. "New lead created") + sender domain allowlist
- Parsing template generated once at onboarding from 2–3 example emails; field extraction (name, phone, email, message) uses saved template — **no per-email LLM call**

## WhatsApp Business Ingestion Detail

- WhatsApp Business API only — not the consumer WhatsApp Business app
- Tenant provides Meta Business Account ID, Phone Number ID, Access Token during onboarding
- Meta sends webhooks to Ingestion Service on every incoming message
- Filtering: [[concepts/two-stage-lead-filtering]] — rule stage first (~30–40% noise eliminated), then LLM classification
- LLM classifier calibration: default-to-LEAD when uncertain (missing a lead > processing noise)

## Instagram DMs Ingestion Detail

- Account must be Business or Creator, linked to a Facebook Page
- Tenant completes OAuth flow via Instagram Graph API during onboarding
- Meta sends webhooks to Ingestion Service on new DMs
- Filtering: [[concepts/two-stage-lead-filtering]] + Instagram-specific rules:
  - Sender with very few followers, account <30 days old, or bot-flagged → dropped at rule stage
  - Story reactions and emoji-only messages → dropped at rule stage
  - Voice notes → transcribed via speech-to-text, then classified as text
  - Image-only messages → logged but not classified in Phase 0

## Google Spreadsheet Ingestion Detail

- Service account email provided to tenant; tenant shares sheet with read-only access
- Default poll: every 15 minutes (configurable per tenant)
- Column mapping: LLM reads headers at setup and suggests field mappings; tenant confirms in one step
- Watermark column: tenant identifies a timestamp or auto-increment ID column to detect new/updated rows efficiently on each poll
- No LLM noise filtering — tenant-curated source; validation only (discard rows where both phone and email are empty)

## Cross-Source Concerns

**Normalization:** Each source produces a different format. Ingestion Service adapters convert all four into a single normalized internal message structure before passing to downstream services.

**Deduplication:** Across all four sources, matched on phone + email. A prospect who contacts on WhatsApp and also appears in the spreadsheet is unified into one lead with both touchpoints recorded.

**Immutable intake event log:** Every incoming record (message, email, row) is stored before any filtering or processing. Enables replay if filtering rules change or a processing bug is discovered.

**Tenant feedback:** Leads created from filtered sources (WhatsApp, Instagram) include a "This is not a lead" option in the tenant dashboard. Feedback collected and used to improve classifier performance — see [[concepts/feedback-loop]].

## Tensions & Contradictions

- The WhatsApp/Instagram LLM classification step uses a "fast, low-cost LLM (such as Claude Haiku or GPT-4o-mini)" — this appears to be a pre-pipeline LLM call separate from the Message Parser (Haiku) described in the orchestration layer spec. Whether these are the same invocation or two distinct LLM calls needs clarification. (sources: [[sources/2026-lead-ingestion-strategy]], [[analyses/orchestration-layer-spec]])
- The immutable intake event log is described without specifying which entity stores it. Unclear whether it maps to the existing `lineage_record` in the 32-entity catalog or requires a new entity. See [[concepts/data-entity-model]] for current entity list.
- Google Spreadsheet poll interval (15 min, configurable) is not yet mapped to `tenant_config` operational limits fields specified in [[analyses/client-config-schema-defaults]].

## Related Concepts

- [[concepts/two-stage-lead-filtering]] — the noise filtering mechanism for WhatsApp and Instagram
- [[concepts/b2c-data-acquisition]] — historical B2C data (order + chat history) that backs enrichment once a lead enters via one of these sources
- [[concepts/lead-pipeline-architecture]] — these sources trigger Pipeline 1; normalization output is the input to Data Gather / Enrichment
- [[concepts/feedback-loop]] — tenant "not a lead" flag from ingestion layer feeds classifier improvement

## Sources

- [[sources/2026-lead-ingestion-strategy]] — primary source; full 4-source spec, filtering design, cross-source concerns
- [[sources/2026-b2c-data-acquisition]] — B2C historical data; complements real-time ingestion for B2C tenant scoring
