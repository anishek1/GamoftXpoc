---
type: analysis
question: "Final developer scope for Epic 3 — Lead Ingestion"
date: 2026-06-06
tags: [epic-3, lead-ingestion, webhooks, oauth, meta, whatsapp, instagram, facebook, lead-ads, email, google-sheets, two-stage-filter, deduplication, scope, developer-spec]
status: FINAL — approved for Sprint 3 development
---

# Epic 3 — Developer Scope

**What this builds:** All inbound lead channels (WhatsApp, Instagram, Facebook, Lead Ads, email, Google Sheets, Google Forms) are wired up and delivering events. Every DM lead passes through a two-stage noise filter. Leads that survive land in `captured` state. NOISE exits immediately with zero enrichment or LLM scoring calls.

---

## Scope Boundary

**All files live inside `modules/lead_ingestion/`. Nothing outside.**

Out of scope for this epic:
- Epic 1 — auth, Clerk JWT, RBAC, multi-tenancy shell
- Epic 2 — tenant onboarding, Pipeline 2 agents, `PromptRegistry`, persona/ICP/signal generation
- Epic 4 — enrichment, signal extraction (all 13 types), Rating Agent, scoring, PII encryption, bucketize
- Epic 5 — delivery, salesperson UI, CRM sync
- Frontend connector-setup UI — consumed via the API endpoints built here; not built here
- `ChannelConnection` SQLAlchemy model definition — created in Epic 2 `db/models.py`; Epic 3 writes to the existing table only

**Epic 3 handoff to Epic 4:** Epic 3 produces a `Lead` record with `pipeline_stage = captured` (or `insufficient_signal` / `existing_customer` / `awaiting_clarification`) and a corresponding `intake_event_log` entry. Epic 4 picks up every lead at `captured` and runs enrichment → signal extraction → scoring.

---

## Architectural Decisions (Locked)

| # | Decision | Resolution |
|---|---|---|
| 1 | Signal extractor ownership | **Epic 4.** Epic 3 ends at `captured`. The strategy-pattern signal extractor registry (all 13 types, each returning `(detected, value, evidence)`) is built in Epic 4 / Sprint 4 Dev B. Epic 3 does not evaluate signal values. |
| 2 | Lead Ad pipeline entry | **Bypass Message Parser.** Lead Ad events skip the two-stage filter (rule filter + Message Parser) and arrive pre-structured. Epic 3 normalises form fields into `NormalisedChannelEvent` and routes directly to pre-flight. |
| 3 | EXISTING_CUSTOMER routing | **Locked 2026-05-22.** Message Parser returns `EXISTING_CUSTOMER` → `pipeline_stage = 'existing_customer'` (terminal); CRM sync event emitted; no scoring; no lead card created. See [[analyses/orchestration-layer-spec]] §8.1. |
| 4 | UNCLEAR routing | **Locked 2026-05-22.** Message Parser returns `UNCLEAR` → `pipeline_stage = 'awaiting_clarification'`; lead paused; salesperson notified; 24h timeout via workflow engine `waitForEvent`; exempt from crash recovery while paused. See [[analyses/orchestration-layer-spec]] §8.1. |
| 5 | Webhook + polling hybrid | Both run in parallel. Webhooks are primary; polling is failsafe. Event deduplication by `platform_event_id` (ON CONFLICT DO NOTHING) ensures idempotency at the DB write level. |
| 6 | HMAC validation on raw bytes | Signature validated on the raw request body **before** JSON parsing. Tampered or unparseable payloads return 403. See [[analyses/meta-integration-implementation]] for the locked implementation. |
| 7 | OAuth state signing | HMAC-signed `state` parameter shared across all three Meta OAuth flows (WhatsApp Embedded Signup, Instagram Login, Facebook standard OAuth). Signing key = per-tenant secret from AWS Secrets Manager. |
| 8 | Instagram token lifecycle | 60-day expiry token. Daily refresh job: refresh when `expires_at - NOW() < 7 days`. If already expired on check: mark `status = expired`, alert, notify tenant to redo OAuth. No server-side recovery after expiry. |
| 9 | Google Sheets column mapping | LLM-assisted once at setup only. Confirmed mapping stored in `lead_form_field_map`. No per-row LLM call. Watermark column (timestamp or auto-increment ID) drives delta detection on each 15-min poll. No LLM noise filter — spreadsheet is a tenant-curated source. |
| 10 | Email structural parsing | Template generated once at onboarding from 2–3 example emails via LLM. No per-email LLM call at ingestion time. Noise filtered by subject keyword match + sender allowlist. |
| 11 | Pre-flight HALT conditions | Missing active persona → HALT; missing signal definitions → HALT; missing active prompt template → HALT. Lead does not advance past `captured` until all three pass. |
| 12 | Deduplication key priority | Phone match wins; email second; name + location fallback. Duplicate merged (both touchpoints recorded on one lead), not double-counted. |
| 13 | ChannelConnection model ownership | Model defined in Epic 2 `db/models.py`. Epic 3 uses its own `db/repository.py` to read and write this table. The OAuth completion handler writes `status = active`. Epic 3 does not redefine the model. |
| 14 | Google Forms ingestion approach | **Apps Script webhook — not polling.** Google Forms has no native push API; polling via a linked Sheet introduces up to 15-min delay. Instead: tenant installs a pre-generated Apps Script snippet (tenant endpoint URL + HMAC secret pre-filled) that fires `onFormSubmit` and POSTs to `POST /channels/inbound/google-forms`. Delay: ~1–3 seconds. Form submissions enter as `event_type='lead_ad'` (structured, tenant-curated source) — bypass two-stage filter and Message Parser, same as Lead Ads. |
| 15 | CSV / XLSX file upload | **Rule-based column mapping — no LLM call.** Tenant uploads a CSV or XLSX file via `POST /channels/inbound/file-upload`. The system parses the file, reads the column headers, and maps them to standard fields using an extended `STANDARD_FIELD_MAP` (common CRM export variants: "Mobile" → phone, "Phone Number" → phone, "Email Address" → email, etc.). Unrecognised columns → `extra_fields` JSONB — not discarded. No LLM call at upload time. Each row produces a `NormalisedChannelEvent(event_type='lead_ad', channel='file_upload')` and bypasses the two-stage filter (tenant-curated source). File size limit: 10MB / 5,000 rows — exceed either → 422. Files above 100 rows are processed asynchronously via Inngest; the endpoint returns a job ID immediately. |

---

## Folder Structure

```
modules/lead_ingestion/
├── __init__.py
├── router.py                  FastAPI endpoints: OAuth initiation + callback, webhook receiver, connector status
├── worker.py                  Registers webhook processor, polling jobs, Instagram refresh job as background tasks
├── webhook_receiver.py        HMAC validation + payload routing by channel (WA / IG / FB)
├── lead_retrieval_worker.py   Lead Ads: fetch lead form data from Meta Graph API with race-condition retry (3s)
├── polling_service.py         Polling fallback: per-channel poll loop, watermark tracking, dedup by platform_event_id
├── normaliser.py              NormalisedChannelEvent builder — one adapter per source (WA / IG / FB / Lead Ads / email / sheets)
├── two_stage_filter.py        Rule filter (regex/heuristics) → Message Parser (Haiku) → LEAD / NOISE / EXISTING_CUSTOMER / UNCLEAR
├── haiku_client.py            Anthropic claude-haiku-4-5 wrapper (Message Parser only). Retries on rate limit (max 3, exponential backoff). Raises HaikuClientError on hard failure.
├── pre_flight.py              Persona present? Signal defs present? Active prompt? → HALT or PASS
├── deduplicator.py            Phone-first dedup → email → name+location fallback; merge touchpoints
├── intake_logger.py           Writes every inbound record to intake_event_log (immutable); writes discard_reason on NOISE
├── instagram_token_refresh.py Daily scheduled job: query channel_connections WHERE channel_type='instagram'; refresh tokens expiring within 7 days; alert on expired
├── email_inbound.py           Inbound email handler: sender allowlist + subject keyword filter; structural template parse; produce NormalisedChannelEvent
├── sheets_poller.py           Google Sheets service account poll (15-min interval, configurable per tenant); watermark delta; column mapping lookup from lead_form_field_map
├── google_forms_webhook.py    Google Forms Apps Script inbound handler: HMAC-secret validation, field normalisation via LeadFormFieldMap, Apps Script snippet generator for tenant setup
├── file_upload_handler.py     CSV/XLSX file upload handler: parse file, fuzzy-map column headers via extended STANDARD_FIELD_MAP, produce NormalisedChannelEvent per row, enqueue batch via Inngest
├── oauth/
│   ├── __init__.py
│   ├── whatsapp.py            Embedded Signup flow: Facebook Login for Business → WABA token; writes ChannelConnection
│   ├── instagram.py           Instagram Login OAuth: api.instagram.com → 60-day token; writes ChannelConnection
│   └── facebook.py            Standard OAuth redirect → 3-step token chain → non-expiring Page Access Token; writes ChannelConnection
├── schemas/
│   ├── __init__.py
│   ├── normalised_event.py    NormalisedChannelEvent Pydantic model
│   ├── lead_form.py           Lead Ads form field schema + STANDARD_FIELD_MAP + extra_fields JSONB
│   └── filter_result.py       FilterResult: classification enum + extracted fields + discard_reason
├── db/
│   ├── __init__.py
│   ├── models.py              SQLAlchemy models owned by Epic 3: Lead, IntakeEventLog, LeadFormFieldMap, LeadTouchpoint
│   └── repository.py          Async CRUD for Epic 3 models + ChannelConnection reads/writes (model defined in Epic 2)
└── tests/
    ├── unit/
    └── integration/
```

---

## Task List

Tasks are ordered by dependency. Each task must be complete before dependent tasks begin.

### Group A — Foundation & Data Models

| Task | File(s) | Responsibility | Depends on |
|---|---|---|---|
| A1 | `db/models.py` | SQLAlchemy ORM models owned by Epic 3: `Lead` (with `pipeline_stage`, `source_channel`, `platform_event_id`, `raw_message`, `raw_event_json`), `IntakeEventLog` (immutable; `discard_reason` nullable), `LeadFormFieldMap` (custom column mapping per tenant + form), `LeadTouchpoint` (one row per channel event tied to a Lead). | — |
| A2 | `db/repository.py` | Async CRUD for A1 models. Includes `ChannelConnection` reads (`get_by_phone_number_id`, `get_by_page_id`) and writes (`set_status`, `upsert_credentials_ref`). No business logic. ON CONFLICT DO NOTHING on `IntakeEventLog.platform_event_id`. | A1 |
| A3 | `schemas/normalised_event.py` | `NormalisedChannelEvent` Pydantic v2 model matching Section 14.2 schema: `event_type` (dm\|lead_ad), `channel`, `tenant_id`, `connection_id`, `platform_event_id`, `timestamp`, sender IDs, `raw_message` (nullable), `lead_form_fields` (nullable). | — |
| A4 | `schemas/lead_form.py` | `LeadFormFields` Pydantic model: standard fields (`email`, `phone`, `full_name`, `company_name`, `job_title`). `STANDARD_FIELD_MAP` dict for Meta → internal name normalisation. `extra_fields: dict` for custom form columns (stored as JSONB). | — |
| A5 | `schemas/filter_result.py` | `FilterResult`: `classification` enum (LEAD / NOISE / EXISTING_CUSTOMER / UNCLEAR), `extracted_fields: dict`, `discard_reason: str | None`, `raw_label: str | None` (Haiku raw output for audit). | — |
| A6 | `haiku_client.py` | Async wrapper for `claude-haiku-4-5-20251001`. Accepts system + user messages; returns structured JSON. Retries on rate limit (max 3, exponential backoff). Raises `HaikuClientError` on hard failure. Used exclusively by `two_stage_filter.py`. | — |

---

### Group B — Meta Webhook Receiver & OAuth

| Task | File(s) | Responsibility | Depends on |
|---|---|---|---|
| B1 | `webhook_receiver.py` | HMAC-SHA256 validation on raw request bytes (`X-Hub-Signature-256`) before JSON parse. Route by `payload["object"]`: `"whatsapp_business_account"` → WhatsApp path, `"instagram"` → Instagram path, `"page"` → Facebook/Lead Ads path. Return HTTP 200 immediately; enqueue for async processing. Return 403 on HMAC failure. | A2, A3 |
| B2 | `oauth/whatsapp.py` | WhatsApp Embedded Signup: Facebook Login for Business flow. Receives WABA token from Meta. Signs `state` param with tenant HMAC. On callback: validate state, store non-expiring Business Integration System User token in AWS Secrets Manager (credentials_ref only in DB), write `ChannelConnection(channel_type='whatsapp', status='active')`. | A2 |
| B3 | `oauth/instagram.py` | Instagram Login OAuth via `api.instagram.com/oauth/authorize`. 60-day expiry token. Signs `state` param with tenant HMAC. On callback: validate state, exchange code for token, store in Secrets Manager, write `ChannelConnection(channel_type='instagram', status='active', expires_at=now+60d)`. | A2 |
| B4 | `oauth/facebook.py` | Standard OAuth redirect → short-lived user token → long-lived user token → non-expiring Page Access Token (3-step chain). Signs `state` param with tenant HMAC. On callback: complete chain, store Page Access Token in Secrets Manager, write `ChannelConnection(channel_type='facebook', status='active')`. | A2 |
| B5 | `lead_retrieval_worker.py` | Lead Ads: on `leadgen` webhook event, fetch lead form data from Meta Graph API using `leadgen_id`. Race condition retry: catch `MetaApiError(code=100)`, wait 3s, retry once. Normalise form fields using `STANDARD_FIELD_MAP`; unknown fields → `extra_fields` JSONB. Produce `NormalisedChannelEvent(event_type='lead_ad')`. | A3, A4 |
| B6 | `router.py` (OAuth + webhook routes) | FastAPI endpoints: `GET /channels/oauth/{channel}/start` (initiate OAuth, return redirect URL), `GET /channels/oauth/{channel}/callback` (handle OAuth callback → write ChannelConnection), `POST /channels/webhook` (Meta webhook receiver — delegates to B1), `GET /channels/webhook` (Meta hub challenge verification), `GET /channels/{connection_id}/status` (connector health), `POST /channels/inbound/google-forms` (Google Forms Apps Script submissions — delegates to D5), `POST /channels/inbound/file-upload` (CSV/XLSX file upload — delegates to D6; multipart/form-data; returns result or `{"job_id": ..., "row_count": ...}` for async batches). All tenant-scoped; require authenticated tenant. | B1, B2, B3, B4, D5, D6 |

---

### Group C — Normalisation, Filter & Routing

| Task | File(s) | Responsibility | Depends on |
|---|---|---|---|
| C1 | `normaliser.py` | One adapter per source. Converts raw Meta payload / email / sheets row → `NormalisedChannelEvent`. WhatsApp adapter reads `phone_number_id`, `wa_id`, `text.body`. Instagram adapter reads `sender.id` (IGSID), message text or voice note transcript. Facebook adapter reads `sender.id` (PSID). Lead Ads adapter delegates to `lead_retrieval_worker.py`. Email adapter reads parsed subject + body fields. Sheets adapter reads mapped columns from `LeadFormFieldMap`. | A3, A4 |
| C2 | `two_stage_filter.py` | DM path only. Stage 1 — rule filter: discard greetings, one-word replies, emoji-only messages, story reactions, verified business senders, numbers already marked not-a-lead. ~30–40% eliminated without Haiku call. Stage 2 — Message Parser: send surviving message to Haiku with classification prompt; parse `FilterResult`. Calibration: default-to-LEAD when uncertain. Voice notes receive transcript (from speech-to-text) before Stage 1. Image-only messages: Stage 1 logs to `IntakeEventLog` with `discard_reason = 'image_only_phase0'`; no Stage 2 call. **NOISE outcome (Stage 1 or Stage 2):** creates a `Lead` with `pipeline_stage = 'insufficient_signal'` (terminal) — pipeline stops here; no pre-flight, no dedup advance. | A5, A6, C1 |
| C3 | `pre_flight.py` | Checks three conditions for a `LEAD`-classified event: (1) tenant has `Persona` with `status = active`; (2) tenant has at least one `Signal` with `status = active`; (3) tenant has `PromptRegistry` with `is_active = True`. Any check fails → HALT: set `pipeline_stage = 'captured'` with `pre_flight_block_reason`; write to `IntakeEventLog`; do not advance. All three pass → PASS. | A2 |
| C4 | `deduplicator.py` | On LEAD PASS: look up existing `Lead` by phone (E.164 normalised), then email, then name + location fallback. If match: add a `LeadTouchpoint` row to the existing lead (both arrival events recorded); do not create a new lead. If no match: create a new `Lead`. Ensures a prospect contacting via two channels is one lead with two touchpoints. | A1, A2 |
| C5 | `intake_logger.py` | Writes every inbound raw record to `IntakeEventLog` regardless of classification. Fields: `platform_event_id`, `tenant_id`, `channel`, `raw_payload_json`, `classification`, `discard_reason` (null on LEAD), `ingested_at`. ON CONFLICT (`platform_event_id`) DO NOTHING for idempotency. Immutable — no update or delete path. | A1, A2 |
| C6 | `worker.py` | Registers Epic 3 background jobs with Inngest: webhook event processor (C1 → C2 → C3 → C4 → C5), polling service scheduler (D1, D2), Instagram token refresh scheduler (D3). Handles retry policy for async jobs: 1 retry on transient failure; on 2nd failure write to dead-letter queue and alert. | B1, C1–C5, D1–D3 |

---

### Group D — Polling, Email & Sheets

| Task | File(s) | Responsibility | Depends on |
|---|---|---|---|
| D1 | `polling_service.py` | Per-channel polling fallback. Runs in parallel to webhooks. On each poll cycle: fetch recent events from Meta Graph API using stored token; compare against `IntakeEventLog.platform_event_id` (ON CONFLICT DO NOTHING prevents duplicates). Polling interval: configurable per tenant via `tenant_config`; default 15 min. Produces `NormalisedChannelEvent` events identical to webhook path. | A2, C1 |
| D2 | `email_inbound.py` | Inbound email handler for unique per-tenant address (`tenant-{id}@leads.yourplatform.com`). Sender allowlist check + subject keyword filter (both configurable in `tenant_config`). Parse using structural template stored in `LeadFormFieldMap` (generated once at onboarding). Produce `NormalisedChannelEvent(event_type='dm', channel='email')`. Noise filtered at rule level — no Haiku call. | A2, A3, C1 |
| D3 | `instagram_token_refresh.py` | Daily scheduled job (Inngest scheduled function). Query `channel_connection WHERE channel_type = 'instagram' AND status = 'active'`. For each: fetch token from Secrets Manager; check `expires_at`. If `expires_at - NOW() < 7 days` AND token not yet expired: call Meta Graph API token refresh endpoint; update Secrets Manager; update `expires_at` in `channel_connection`. If already expired: set `status = 'expired'`; emit alert; notify tenant to redo OAuth — no server-side recovery. | A2 |
| D4 | `sheets_poller.py` | Google Sheets ingestion via service account (read-only). 15-min poll interval (configurable per tenant). Read watermark value from `channel_connection.metadata->>'last_watermark'`; fetch only rows newer than watermark. Map columns using `LeadFormFieldMap` for this tenant + sheet. Produce one `NormalisedChannelEvent(event_type='lead_ad', channel='sheets')` per row (no noise filter — tenant-curated source). Update watermark after successful batch. | A2, A4, C1 |
| D5 | `google_forms_webhook.py` | Google Forms real-time inbound via Apps Script trigger. On `POST /channels/inbound/google-forms`: validate `X-Tenant-Secret` header (HMAC-signed token stored in Secrets Manager per tenant; maps request to tenant without URL path param). Map form field names to standard fields using `LeadFormFieldMap` (same setup as Sheets; LLM column mapping done once at connector setup). Produce `NormalisedChannelEvent(event_type='lead_ad', channel='google_forms')`. Also exposes `generate_apps_script_snippet(tenant_id) → str` — called during connector setup to generate the pre-filled Apps Script code the tenant pastes into Google Apps Script Editor. | A2, A3, A4 |
| D6 | `file_upload_handler.py` | CSV/XLSX file upload. On `POST /channels/inbound/file-upload` (multipart/form-data): validate file type (csv/xlsx only) and size (max 10MB, max 5,000 rows — exceed either → 422). Parse using `csv.DictReader` for CSV, `openpyxl` for XLSX. Read column headers; map to standard fields using extended `STANDARD_FIELD_MAP` (covers common CRM export variants: "Mobile"/"Cell"/"Phone Number" → phone, "Email Address" → email, "Full Name"/"Contact Name" → full_name, etc.). **Every column is preserved — no data is dropped.** Recognised columns → mapped standard fields. Unrecognised columns (e.g. "Budget Range", "Notes", "Source Campaign", "Last Purchase Date") → `extra_fields` JSONB verbatim (original column name as key, original cell value as value). Complete raw row stored in `raw_event_json` on the `Lead` record. Produce one `NormalisedChannelEvent(event_type='lead_ad', channel='file_upload')` per row. Files ≤ 100 rows: process synchronously, return result immediately. Files > 100 rows: enqueue full batch as single Inngest job, return `{"job_id": "<id>", "row_count": N}` immediately. All rows bypass two-stage filter (tenant-curated source). Rows where phone AND email AND name are all missing: still create a `Lead`, set `pre_flight_block_reason = 'insufficient_identity_fields'`, write to `IntakeEventLog` — do not discard. Do not halt the batch on any single-row error. | A2, A3, A4 |

---

### Group T — Tests

| Task | What it covers | Depends on |
|---|---|---|
| T1 | **Unit tests — HMAC & OAuth:** Valid HMAC signature passes; tampered payload returns 403; `sign_state` / `verify_state` round-trip; WhatsApp/IG/FB OAuth state validation rejects forged state. | B1–B4 |
| T2 | **Unit tests — Filter:** Rule filter discards emoji-only, greeting-only, story reaction messages without Haiku call; Message Parser returns LEAD / NOISE / EXISTING_CUSTOMER / UNCLEAR for fixture inputs; NOISE path writes zero enrichment calls. | C2, A6 |
| T3 | **Unit tests — Dedup & Pre-flight:** Same phone number on two events → one Lead + two Touchpoints; pre-flight HALT fires correctly for each missing condition (persona / signals / prompt individually). | C3, C4 |
| T4 | **Unit tests — Instagram refresh job:** Mocked clock at `expires_at - 6 days` → refresh called; mocked clock at `expires_at + 1 day` (already expired) → status set to expired, no refresh attempted; mocked clock at `expires_at - 10 days` → no action. | D3 |
| T5 | **Unit tests — Dedup idempotency:** Same `platform_event_id` arriving twice (webhook + poll) → ON CONFLICT DO NOTHING → `IntakeEventLog` has exactly one row; Lead created exactly once. | C5, D1 |
| T6 | **Integration test — WhatsApp DM golden path:** Fixture WA DM payload → HMAC validates → normalise → rule filter passes → Message Parser returns LEAD → pre-flight passes → dedup creates new Lead → `pipeline_stage = captured`. Assert: one `Lead`, one `IntakeEventLog` row, zero enrichment calls, zero Sonnet calls. | All groups |
| T7 | **Integration test — Lead Ad golden path:** Fixture Lead Ad webhook → `lead_retrieval_worker` fetches form fields → normalise → bypass two-stage filter → pre-flight passes → dedup → `pipeline_stage = captured`. Assert: `source_channel = 'facebook_lead_ad'`, no Haiku call, `lead_form_fields` populated. | B5, C3, C4 |
| T8 | **Integration test — NOISE exit:** Fixture WA DM classified as NOISE by rule filter → assert `IntakeEventLog.classification = 'noise'`, `discard_reason` set, `Lead` created with `pipeline_stage = 'insufficient_signal'` (terminal), no Haiku call, no enrichment call, no Sonnet call. | C2, C5 |
| T9 | **Integration test — Google Forms golden path:** Fixture Apps Script POST payload with valid `X-Tenant-Secret` → field normalisation via `LeadFormFieldMap` → bypass two-stage filter → pre-flight passes → dedup → `pipeline_stage = 'captured'`. Assert: `source_channel = 'google_forms'`, no Haiku call, `lead_form_fields` populated. Invalid secret → 403. | D5, C3, C4 |
| T10 | **Integration test — CSV/XLSX file upload golden path:** Fixture CSV with mixed column name variants ("Mobile", "Email Address", "Contact Name") plus unrecognised columns ("Budget Range", "Notes") → headers fuzzy-mapped → rows produce `NormalisedChannelEvent(channel='file_upload')` → bypass two-stage filter → pre-flight passes → dedup → `pipeline_stage = 'captured'`. Assert: no Haiku call, `extra_fields` contains all unrecognised columns verbatim, `raw_event_json` contains full original row, `lead_form_fields` correct. Row with no phone/email/name: Lead created with `pre_flight_block_reason = 'insufficient_identity_fields'` — not discarded. File exceeding 5,000-row limit → 422. File with invalid type (e.g. `.docx`) → 422. | D6, C3, C4 |

---

## Summary

| Group | Tasks | Files |
|---|---|---|
| A — Foundation & Models | A1–A6 | 6 files |
| B — Meta Webhook & OAuth | B1–B6 | 6 files (receiver + 3 OAuth handlers + retrieval worker + router) |
| C — Normalisation, Filter & Routing | C1–C6 | 6 files |
| D — Polling, Email, Sheets & Forms | D1–D6 | 6 files |
| T — Tests | T1–T10 | unit/ + integration/ |
| **Total** | **34 tasks** | **24 files** |

---

## Data Flow

```
Inbound events (all channels)
        │
        ├─ WhatsApp DM / Instagram DM / Facebook DM
        │       │
        │       ├─ [B1] webhook_receiver     HMAC → route → enqueue
        │       │   OR
        │       └─ [D1] polling_service      poll → dedup by platform_event_id
        │               │
        │               ▼
        │       [C1] normaliser              raw payload → NormalisedChannelEvent
        │               │
        │       [C2] two_stage_filter        rule filter (no Haiku) → Haiku classifier
        │               │
        │           ┌───┴────────────────────────────────┐
        │         NOISE                            LEAD / EC / UNCLEAR
        │           │                                    │
        │   Lead created:                        [C3] pre_flight
        │   pipeline_stage =                           │
        │   'insufficient_signal' (terminal)  PASS ────┤──── HALT (captured, blocked)
        │   [C5] intake_logger writes                  │
        │   discard_reason; zero enrichment    [C4] deduplicator
        │   calls; zero LLM calls
        │                                             │
        │                                     phone/email/name match?
        │                                     Yes → add Touchpoint
        │                                     No  → new Lead
        │                                             │
        │                               pipeline_stage = 'captured'
        │
        ├─ Facebook Lead Ads / Instagram Lead Ads
        │       │
        │       ├─ [B1] webhook_receiver     HMAC → leadgen event → enqueue
        │       │       │
        │       └─ [B5] lead_retrieval_worker  fetch form fields → race-condition retry
        │               │
        │       [C1] normaliser              form fields → NormalisedChannelEvent(event_type='lead_ad')
        │               │
        │       ── BYPASSES two_stage_filter (no rule filter, no Haiku call) ──
        │               │
        │       [C3] pre_flight  →  [C4] deduplicator  →  pipeline_stage = 'captured'
        │
        ├─ Email
        │       │
        │       └─ [D2] email_inbound        sender allowlist + subject filter → template parse
        │               │
        │       [C1] normaliser  →  [C3] pre_flight  →  [C4] deduplicator  →  captured
        │
        ├─ Google Sheets
        │       │
        │       └─ [D4] sheets_poller        15-min poll → watermark delta → column map
        │               │
        │       [C1] normaliser  →  [C3] pre_flight  →  [C4] deduplicator  →  captured
        │
        ├─ Google Forms
        │       │
        │       └─ [D5] google_forms_webhook  Apps Script POST → HMAC-secret validation → field normalise via LeadFormFieldMap
        │               │
        │       ── BYPASSES two-stage filter (structured, tenant-curated source) ──
        │               │
        │       [C3] pre_flight  →  [C4] deduplicator  →  pipeline_stage = 'captured'
        │
        └─ CSV / XLSX File Upload
                │
                └─ [D6] file_upload_handler   multipart POST → validate size/type → parse rows → fuzzy-map headers via STANDARD_FIELD_MAP
                        │
                ── BYPASSES two-stage filter (tenant-curated source) ──
                        │
                [C3] pre_flight  →  [C4] deduplicator  →  pipeline_stage = 'captured'
                (≤100 rows: sync response | >100 rows: Inngest job, returns job_id)

All paths → [C5] intake_logger writes every event to IntakeEventLog (immutable)

Routing by Message Parser classification (DM path only):
  LEAD              → pre_flight → dedup → pipeline_stage = 'captured'
  NOISE             → pipeline_stage = 'insufficient_signal' (terminal); zero downstream
  EXISTING_CUSTOMER → pipeline_stage = 'existing_customer' (terminal); CRM sync emitted
  UNCLEAR           → pipeline_stage = 'awaiting_clarification'; 24h waitForEvent timeout

EPIC 3 ENDS HERE. Epic 4 picks up every lead at pipeline_stage = 'captured'.
```

---

## Key Constraints

- **Credentials never in DB.** `channel_connection.credentials_ref` stores the AWS Secrets Manager vault path only. Token bytes are stored and read exclusively via Secrets Manager.
- **Webhook 200 before processing.** HMAC validation is the only synchronous step. After HMAC passes, enqueue immediately and return 200. All normalisation, filtering, dedup, and logging are async.
- **NOISE creates a terminal Lead with zero downstream calls.** A NOISE-classified message creates a `Lead` with `pipeline_stage = 'insufficient_signal'` (terminal) and writes to `intake_event_log` with `discard_reason`. It must produce no enrichment call, no Scoring Agent call, and no Haiku call (rule-filter discards without Haiku; Message Parser NOISE result discards before pre-flight). Enforced in T8.
- **`intake_event_log` is immutable.** No update or delete paths. Every raw inbound record is stored here for replay. ON CONFLICT DO NOTHING on `platform_event_id`.
- **`awaiting_clarification` is non-terminal.** Crash recovery job must exclude `pipeline_stage = 'awaiting_clarification'` from its resume sweep (see [[analyses/orchestration-layer-spec]] §8.3). Epic 3 sets this state; Epic 4's orchestrator honours it.
- **Instagram expiry is a production risk.** The 60-day refresh job (D3) must be deployed and tested before go-live. Acceptance criterion: unit tests against mocked clock covering all three states (needs refresh / already expired / no action needed).
- **All Haiku calls go through `haiku_client.py`.** No direct Anthropic SDK calls outside that file. Same isolation pattern as `sonnet_client.py` in Epic 2.
- **`ChannelConnection` model is read-only for Epic 3.** Epic 3 reads and writes rows but does not modify the SQLAlchemy model definition — that lives in Epic 2 `modules/tenant_onboarding/db/models.py`. Epic 3's `db/repository.py` imports the model from Epic 2.
- **Lead Ads enter pre-structured.** The two-stage filter is a DM-only path. Lead Ad events go directly from normaliser → pre-flight → dedup. No Haiku call is ever made for a Lead Ad event.
- **Google Sheets polling interval is configurable.** Default 15 minutes; configurable per tenant via `tenant_config`. Follow the same pattern as other operational limits in the tenant config schema.
- **CSV/XLSX uploads preserve every column — no silent drops.** Recognised columns map to standard fields; unrecognised columns (e.g. "Notes", "Budget", "Source Campaign") go into `extra_fields` JSONB verbatim. The complete raw row is stored in `raw_event_json` on the `Lead`. These fields are LLM context for Epic 4's Rating Agent — dropping them degrades scoring quality. Rows with no identifiable fields (no phone, email, or name) still create a Lead and are flagged, never silently discarded.
- **Google Forms uses HMAC-secret auth, not OAuth.** The Apps Script endpoint cannot use JWT (no browser session). Authentication is a per-tenant HMAC-signed secret stored in Secrets Manager and embedded in the generated Apps Script snippet at connector setup. Invalid or missing secret → 403; do not return tenant details in the error body.
