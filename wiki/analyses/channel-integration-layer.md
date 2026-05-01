---
type: analysis
question: "How do tenants connect external platforms, and how do lead events enter Pipeline 1?"
date: 2026-04-28
tags: [channel-integration, oauth, webhooks, event-detection, tenant-onboarding, channel-connection, meta, whatsapp, instagram]
sources_consulted:
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/lead-enrichment-architecture]]"
  - "[[concepts/data-entity-model]]"
status: COMPLETE
---

# Channel Integration Layer

**Question:** How do tenants connect external platforms, and how do lead events enter Pipeline 1?
**Date:** 2026-04-28  
**Detailed API spec:** [[analyses/meta-platform-api-deep-research]] — precise OAuth flows, token types, all webhook payload schemas, rate limits, multi-tenant patterns  
**Implementation detail:** [[analyses/meta-integration-implementation]] — Embedded Signup, webhook routing logic, Lead Ads retrieval, implementation checklist

---

## What This Layer Is

The Channel Integration Layer sits upstream of Pipeline 1. It is responsible for:

1. Connecting tenant external accounts (Meta, WhatsApp, LinkedIn, website, etc.) to the system
2. Receiving events from those platforms (messages, form fills, ad leads)
3. Normalising each platform-specific payload into a standard `NormalisedEvent`
4. Triggering Pipeline 1

Pipeline 1 starts at Data Gather. The Channel Integration Layer is what ensures there is data to gather.

---

## The channel_connection Entity

A new data entity is required — not yet in [[concepts/data-entity-model]] Group A. One record per platform per tenant.

```
channel_connection {
  connection_id
  tenant_id
  channel_type:      facebook | instagram | whatsapp | linkedin
                     | website | google_ads | meta_ads | manual
  auth_method:       oauth | api_key | embed_script
  credentials_ref:   vault_path   ← token NEVER stored in DB directly
  webhook_endpoint:  url registered with the platform
  status:            active | expired | revoked | error
  connected_at:      timestamp
  last_event_at:     timestamp
  metadata:          { page_id, waba_id, ig_account_id, ... }
}
```

When a tenant connects Meta, they get separate `channel_connection` records for Facebook, Instagram, and WhatsApp — same OAuth flow, different tokens and webhook subscriptions per surface.

---

## Platform Connection — OAuth Flow

### Meta (Facebook Pages + Instagram Business + WhatsApp Business)

```
Tenant: Settings → "Connect Meta"
        ↓
Redirect to facebook.com/dialog/oauth
  ?client_id={app_id}
  &scope=pages_messaging,instagram_manage_messages,
         whatsapp_business_messaging,leads_retrieval
        ↓
Tenant logs in with Facebook Business account
        ↓
Meta consent screen:
  "Allow GamoftX to: Read messages, Access leads..."
        ↓
Tenant taps Authorize
        ↓
Meta returns auth code
→ Backend exchanges for:
    Page access token     (per Facebook Page)
    Instagram token       (if IG Business account linked)
    WABA token            (if WhatsApp Business account linked)
        ↓
All tokens → AWS Secrets Manager
  key pattern: {tenant_id}/meta/{surface}/access_token
        ↓
Register webhook subscriptions:
  Facebook Page:  messages, leadgen
  Instagram:      messages
  WhatsApp:       messages
        ↓
channel_connection records created (one per surface, status: active)
```

**Why this matters for enrichment:** When a lead DMs the tenant's Instagram Business account, the event payload includes the sender's Instagram user ID. Tier 3 social enrichment requires no identity lookup — the handle is already known. See [[analyses/lead-enrichment-architecture]].

### LinkedIn

```
OAuth via LinkedIn Marketing Developer Platform
  scope: r_liteprofile, rw_leads
        ↓
Token stored in Secrets Manager
        ↓
Webhook for Lead Gen Form submissions
        ↓
channel_connection record created
```

LinkedIn Lead Gen form responses include the submitter's LinkedIn profile data directly. The richest inbound lead source for B2B tenants.

### Website (Tenant's Own Site)

```
Tenant adds JS tracking snippet to their site:
  <script src="https://app.gamoftx.com/track.js"
          data-tenant="{tenant_id}"></script>
        ↓
Snippet captures:
  - Form submissions (any form with data-track="lead")
  - Page views (product, pricing, case_study pages)
  - Time on page
        ↓
Posts to: POST /api/ingest/{tenant_id}/website
        ↓
channel_connection record (type: website, auth_method: embed_script)
```

---

## Event Detection — Webhooks + Polling Hybrid

Both mechanisms run in parallel. Webhooks are primary; polling is the fallback.

### Webhooks (primary — real-time)

When an event happens on a connected platform, the platform POSTs to our endpoint:

```
Lead sends DM / submits form / clicks ad
        ↓
Platform fires POST to:
  https://app.gamoftx.com/webhooks/{platform}/{tenant_id}
        ↓
Webhook receiver:
  1. Validate HMAC-SHA256 signature (shared secret per channel_connection)
  2. Parse platform-specific payload
  3. Normalise → NormalisedEvent
  4. Write: lead record (pipeline_stage: captured) + event record
  5. Trigger Pipeline 1 (trigger_type: webhook)
```

### Polling (fallback — scheduled)

A background job runs every N minutes per tenant × channel pair. Catches webhook delivery failures and platforms without webhook support.

```
Polling job fires for (tenant_id, channel_connection_id)
        ↓
Fetch events since last_event_at from platform API
        ↓
For each new event:
  Dedup check by platform_event_id
  If new: normalise → write lead + event → trigger Pipeline 1
        ↓
Update channel_connection.last_event_at
```

### Failure isolation rule

If one channel fails (API down, token expired, webhook misconfigured):

- Log to `telemetry_event`
- Create `alert_incident` (notify tenant admin)
- All other connected channels continue unaffected
- Polling fallback catches missed events when the channel recovers

One broken channel never stops Pipeline 1 from processing events from the others.

---

## From Platform Payload to NormalisedEvent

Every platform sends events in a different format. A per-platform normalisation adapter converts each to the standard `NormalisedEvent` schema defined in [[analyses/signal-detection-rule-spec]].

| Platform | Raw payload key fields | NormalisedEvent result |
|---|---|---|
| Instagram DM | sender.id, message.text, timestamp | social_profile_id=sender.id, message_content, source_type="instagram_dm" |
| WhatsApp | from (phone), body, timestamp | phone=from, message_content=body, source_type="whatsapp_dm" |
| Facebook DM | sender.id, message.text | social_profile_id=sender.id, message_content, source_type="facebook_dm" |
| Meta Lead Ad | field_data[], leadgen_id, ad_id | form_response={field→value}, ad_campaign_id, source_type="meta_ads_lead" |
| LinkedIn Lead Gen | firstName, lastName, email, formResponse | email, form_response, source_type="linkedin_lead_form" |
| Website form | form fields, page_url, time_on_page_seconds | form_response, page_url, page_type, source_type="website_visit" |

After normalisation, Pipeline 1 operates on a uniform record regardless of which platform the lead came from.

---

## Token Lifecycle Management

Meta tokens expire. Token failures silently break event ingestion if not caught.

```
Platform API returns 401 (token expired / revoked)
        ↓
Webhook receiver / polling job catches the error
        ↓
Update channel_connection.status = "expired"
        ↓
Create alert_incident (type: token_expired)
        ↓
Notify tenant admin via notification channel:
  "Your Meta connection expired. Please reconnect."
        ↓
Tenant completes OAuth flow again
→ new token stored
→ channel_connection.status = "active"
→ polling job catches any missed events since expiry
```

---

## Open Items

- **`channel_connection` entity** must be added to [[concepts/data-entity-model]] Group A (Core Lead Lifecycle)
- **Webhook secret rotation** — how often, which vault path, service restart implications
- **Meta app review requirements** — RESOLVED in [[analyses/meta-platform-api-deep-research]] Section 1.4. All six Facebook permissions + two Instagram permissions + two WhatsApp permissions require Advanced Access + App Review + Business Verification. Clean first submission: 2–7 days. Plan 2-week buffer before target launch. Business Verification can take up to 60 days if additional documents are needed — start early.
- **Instagram token refresh job** — IDENTIFIED in [[analyses/meta-platform-api-deep-research]] Section 1.2. Instagram long-lived tokens expire in 60 days (no permanent equivalent exists). Background job required: check daily, refresh when `expires_in` < 604800. If expired before refresh, tenant must redo OAuth.
- **WhatsApp Embedded Signup vs standard OAuth** — IDENTIFIED in [[analyses/meta-platform-api-deep-research]] Section 1.3. WhatsApp does NOT use a standard OAuth redirect. Requires Embedded Signup flow (Facebook Login for Business product configuration). Returns a Business Integration System User token (non-expiring) rather than a page token.
- **Instagram API path selection** — IDENTIFIED in [[analyses/meta-platform-api-deep-research]] Section 1.2. Must use Instagram API with Instagram Login path (`instagram_business_*` scopes). Old `business_*` scope names deprecated January 27, 2025. Facebook Login path is legacy.
- **Lead Ads two-step retrieval** — IDENTIFIED in [[analyses/meta-platform-api-deep-research]] Section 3.4. The `leadgen` webhook delivers only IDs (`leadgen_id`, `form_id`, `ad_id`) — no form field values. A follow-up `GET /{leadgen_id}` call is required to fetch actual lead data. Must happen immediately on webhook receipt.
- **WhatsApp contact profile picture** — CONFIRMED NOT AVAILABLE in [[analyses/meta-platform-api-deep-research]] Section 5.4. Official Cloud API has no endpoint to retrieve a contact's profile photo. Not a blocker; enrichment falls back to Truecaller for phone-based name lookup.
- **LinkedIn Marketing API allowlist** — LinkedIn requires application approval for the Marketing Developer Platform. Plan for a 2–4 week approval window per tenant.
- **Manual channel** — CSV import and direct entry flow not yet designed
- **Polling interval** — N minutes per channel TBD; tradeoff between recency and API rate limits
- **Dedup strategy for edge cases** — if webhook fires AND polling picks up the same event, dedup by `platform_event_id` must be idempotent at the DB write level
- **Lead Ads form field normalization** — Standard field names (email, phone_number, full_name, etc.) are predictable. Custom fields are form-defined and cannot be predicted. Build step: pre-fetch form definition via `GET /{form_id}?fields=questions` at connection time; store field map per tenant per form; unknown fields land in `extra_fields` JSONB. See [[analyses/meta-platform-api-deep-research]] Section 3.4.
