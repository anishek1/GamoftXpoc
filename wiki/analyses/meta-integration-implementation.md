---
type: analysis
question: "How exactly do you implement WhatsApp Embedded Signup, multi-tenant webhook routing, and Meta Lead Ads retrieval?"
date: 2026-05-01
tags: [meta, facebook, instagram, whatsapp, embedded-signup, webhooks, lead-ads, implementation, channel-integration, multi-tenant]
sources_consulted:
  - "[[analyses/meta-platform-api-deep-research]]"
  - "[[analyses/channel-integration-layer]]"
status: COMPLETE
---

# Meta Integration — Deep Implementation

**Question:** Exact implementation mechanics for WhatsApp Embedded Signup, multi-tenant webhook routing, and Meta Lead Ads retrieval  
**Date:** 2026-05-01  
**Prerequisite reading:** [[analyses/meta-platform-api-deep-research]] (OAuth flows, token types, payload schemas, rate limits)

---

## 1. WhatsApp Embedded Signup — Full Implementation

### 1.1 What It Is

WhatsApp does not use a standard OAuth redirect. Meta built a separate product called **Facebook Login for Business** specifically for SaaS platforms onboarding other businesses' WhatsApp accounts. Add it in the App Dashboard → Add Product → Facebook Login for Business. It is distinct from standard Facebook Login and must be configured separately.

### 1.2 Frontend — JavaScript SDK Setup

Load the Meta JS SDK on your settings page and launch the popup when the tenant clicks "Connect WhatsApp":

```html
<script>
  window.fbAsyncInit = function() {
    FB.init({
      appId: '{your_app_id}',
      autoLogAppEvents: true,
      xfbml: true,
      version: 'v21.0'
    });
  };
</script>
<script async defer src="https://connect.facebook.net/en_US/sdk.js"></script>
```

```javascript
function launchWhatsAppSignup(tenantId) {
  FB.login(function(response) {
    if (response.authResponse) {
      const code = response.authResponse.code;
      exchangeCodeForToken(code, tenantId);
    } else {
      // tenant cancelled mid-flow — no record created, show retry prompt
    }
  }, {
    config_id: '{your_configuration_id}',   // created once in App Dashboard under Facebook Login for Business
    response_type: 'code',
    override_default_response_type: true,
    extras: {
      setup: {},
      featureType: '',
      sessionInfoVersion: '3',
      state: signState(tenantId),           // signed JWT encoding tenant_id — see Section 1.5
    }
  });
}
```

The `config_id` is a configuration created once in the App Dashboard that pre-selects `whatsapp_business_management` and `whatsapp_business_messaging` scopes so the tenant does not have to choose them manually.

### 1.3 What the Tenant Sees (Popup Flow)

1. Log in to their Facebook Business account (skipped if already logged in)
2. Select or create a Meta Business Portfolio
3. Select or create a WhatsApp Business Account (WABA)
4. Select or register a phone number (OTP verification if registering a new number)
5. Confirm permissions your app is requesting
6. Popup closes; `FB.login` callback fires with the `code`

If the tenant already has a WABA, they select it in step 3 — they do not re-register it.

### 1.4 Backend — Code Exchange

Your backend receives the `code` from the frontend and exchanges it:

```
POST https://graph.facebook.com/v21.0/oauth/access_token
  ?client_id={app_id}
  &client_secret={app_secret}
  &code={code}
```

Response:
```json
{
  "access_token": "EAAB...",
  "token_type": "bearer"
}
```

This is the **Business Integration System User access token**. It is non-expiring. Store it in Secrets Manager at:
```
{tenant_id}/whatsapp/{phone_number_id}/access_token
```

### 1.5 Fetching WABA ID and Phone Number IDs

After the code exchange, use the `granular_scopes` field from a debug token call to find which WABA IDs granted permissions:

```
GET /debug_token?input_token={access_token}&access_token={app_id}|{app_secret}
```

Then enumerate phone numbers for each WABA:

```
GET /{waba_id}/phone_numbers
   ?access_token={access_token}
```

Response gives an array of phone number objects, each with:
- `id` — the `phone_number_id` (your routing key)
- `display_phone_number` — human-readable number
- `verified_name` — the WhatsApp Business display name
- `quality_rating` — GREEN / YELLOW / RED

**One WABA, multiple phone numbers:** Supported. Create one `channel_connection` record per `phone_number_id`, all sharing the same `tenant_id` and `waba_id`.

### 1.6 Webhook Registration on the WABA

After storing the token, subscribe your app to receive events for this WABA:

```
POST /{waba_id}/subscribed_apps
   ?access_token={access_token}
```

No body required. This tells Meta to start delivering `messages` webhook events for this WABA to your app's configured webhook URL. Do this once per WABA at connection time.

### 1.7 The `state` Parameter and Multi-Tenant Security

Pass a signed value (e.g., HMAC-signed `tenant_id`) as `state` in the Embedded Signup extras. When the flow completes, your callback receives it back. This tells your backend which tenant completed the signup, so you know which `channel_connection` records to create. Without `state`, you cannot map the returned `code` to a tenant server-side.

```python
import hmac, hashlib, base64

def sign_state(tenant_id: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), tenant_id.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{tenant_id}:{sig}".encode()).decode()

def verify_state(state: str, secret: str) -> str:
    decoded = base64.urlsafe_b64decode(state).decode()
    tenant_id, sig = decoded.rsplit(':', 1)
    expected = hmac.new(secret.encode(), tenant_id.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid state signature")
    return tenant_id
```

### 1.8 Error Cases

| Scenario | Behaviour |
|---|---|
| Tenant cancels mid-flow | `response.authResponse` is null; no code returned; no record created; show retry prompt |
| Tenant already has a WABA | They select it in the flow; you receive a token for that existing WABA |
| Phone number registered to another WABA | Meta blocks it in the flow; tenant must use a different number |
| Business Verification not complete | Token is issued; API calls succeed; but messaging permission errors occur until verified |
| Token exchange fails | Log error, alert tenant, do not create `channel_connection`; they must retry |

---

## 2. Webhook Routing Logic — Multi-Tenant Implementation

### 2.1 The Core Problem

All tenants share one Meta App. Meta delivers all webhook events — from every tenant's Facebook Page, Instagram account, and WhatsApp number — to one endpoint URL. Routing must identify the correct tenant from the payload within the same request cycle.

### 2.2 Response-First Architecture

Always return HTTP 200 immediately after HMAC validation. Never do synchronous downstream work inside the webhook handler. If your endpoint is slow or throws an error, Meta retries — causing duplicates.

```
Webhook POST arrives
       ↓
Validate HMAC-SHA256 → if invalid: return 403, done
       ↓
Enqueue raw payload + timestamp to internal job queue
       ↓
Return HTTP 200 immediately
       ↓
(async) Worker picks up job → route → normalise → write → Pipeline 1
```

Meta retries failed deliveries for up to 24 hours with exponential backoff. After 24 hours, the event is dropped. Your polling fallback catches anything dropped.

### 2.3 HMAC-SHA256 Validation

Meta signs every POST with your **app secret** (one secret for the whole app, not per-connection). The signature is in `X-Hub-Signature-256` as `sha256={hex_digest}`.

```python
import hmac, hashlib

def validate_meta_signature(
    raw_body: bytes,
    signature_header: str,
    app_secret: str
) -> bool:
    expected = hmac.new(
        app_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    received = signature_header.removeprefix('sha256=')
    return hmac.compare_digest(expected, received)
```

**Critical:** validate on the **raw request body bytes** before any JSON parsing. If your framework auto-parses and you re-serialize for validation, byte representation may differ and validation will fail spuriously.

### 2.4 Facebook and Instagram Routing

The `entry[].id` field is the Page ID (Facebook) or Instagram account ID (Instagram). Look it up in `channel_connection.metadata`:

```sql
SELECT tenant_id, connection_id, channel_type
FROM channel_connection
WHERE metadata->>'page_id' = $1        -- for Facebook
   OR metadata->>'ig_account_id' = $1  -- for Instagram
  AND status = 'active';
```

Add a GIN index on the `metadata` JSONB column. At scale, this lookup is sub-millisecond.

For Facebook, `entry[].id` is always the Page ID. For Instagram, `entry[].id` is the Instagram account ID. Both surface types can share one routing query if you store both IDs in the `metadata` column.

### 2.5 WhatsApp Routing

WhatsApp payloads contain `entry[].changes[].value.metadata.phone_number_id`. This is your routing key:

```sql
SELECT tenant_id, connection_id
FROM channel_connection
WHERE metadata->>'phone_number_id' = $1
  AND channel_type = 'whatsapp'
  AND status = 'active';
```

One tenant can have multiple phone numbers (multiple `channel_connection` rows). The `phone_number_id` uniquely identifies which one received the message.

### 2.6 Distinguishing Message Types Inside the Payload

After routing to a tenant, the worker must determine what kind of event arrived:

**Facebook/Instagram — check `messaging` vs `changes` key:**
```python
for entry in payload['entry']:
    if 'messaging' in entry:
        # Messenger or Instagram DM
        for event in entry['messaging']:
            if 'message' in event:
                handle_dm(event)
            elif 'postback' in event:
                handle_postback(event)
    elif 'changes' in entry:
        for change in entry['changes']:
            if change['field'] == 'leadgen':
                handle_leadgen(change['value'])
            elif change['field'] == 'comments':
                handle_comment(change['value'])
```

**WhatsApp — check for `messages` vs `statuses` inside `value`:**
```python
value = entry['changes'][0]['value']
if 'messages' in value:
    handle_inbound_message(value)
elif 'statuses' in value:
    handle_status_update(value)   # delivery/read receipts — not leads, ignore at MVP
```

### 2.7 Webhook Deduplication

The same event can arrive via webhook and polling fallback. Make the DB write idempotent using a unique constraint on `platform_event_id`:

```sql
INSERT INTO event (platform_event_id, tenant_id, lead_id, channel_type, raw_payload, created_at)
VALUES ($1, $2, $3, $4, $5, NOW())
ON CONFLICT (platform_event_id) DO NOTHING;
```

The second write (whichever arrives second — webhook or poller) silently no-ops. No separate dedup check required.

### 2.8 App-Level vs Page-Level Subscription — Both Required

| Level | What it is | How |
|---|---|---|
| App-level | Webhook URL + verify token for your whole Meta App | App Dashboard → Webhooks → Edit; done once manually |
| Page-level (Facebook) | Start sending events for a specific Page to your app | `POST /{page_id}/subscribed_apps?subscribed_fields=messages,leadgen&access_token={page_token}` |
| App-level (WhatsApp) | Subscribe WABA | `POST /{waba_id}/subscribed_apps?access_token={token}` |

App-level must exist first. If a tenant connects and webhooks do not arrive, check both tiers. The app-level subscription is the most commonly missed step.

### 2.9 Challenge Verification

The GET challenge request fires **once at setup time** — when you first register the webhook URL in the App Dashboard. Your endpoint must respond with the `hub.challenge` value as plain text with HTTP 200 (no JSON wrapper). It does not repeat on subsequent webhook POSTs.

```python
@app.get('/webhooks/meta')
def webhook_verify(hub_mode, hub_challenge, hub_verify_token):
    if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type='text/plain', status_code=200)
    return Response(status_code=403)
```

### 2.10 Multiple Pages / Accounts Per Tenant

A tenant may manage multiple Facebook Pages or Instagram accounts. One `channel_connection` record per Page/account, all with the same `tenant_id`. The OAuth flow returns all Pages via `GET /{user_id}/accounts` — present the tenant with a checklist of which ones to connect. Each selected Page gets its own `channel_connection` record and its own webhook subscription.

### 2.11 Token Revocation Detection

When a tenant removes your app from their Facebook account, the Page-level webhook subscription is automatically removed. You stop receiving webhooks for that Page. The primary signal is silence — no events where events are expected.

Set up a monitoring alert:
```sql
SELECT tenant_id, connection_id, channel_type, last_event_at
FROM channel_connection
WHERE status = 'active'
  AND last_event_at < NOW() - INTERVAL '48 hours'
  AND channel_type IN ('facebook', 'instagram', 'whatsapp');
```

Alert on any active connection with no events in 48 hours. Could be revocation, token expiry, or webhook misconfiguration.

---

## 3. Meta Lead Ads Retrieval — Full Implementation

### 3.1 The Complete Sequence

```
1. Tenant creates a Lead Ad on Facebook or Instagram
2. User sees the ad, fills the form, submits
3. Meta fires leadgen webhook within seconds:

   POST /webhooks/meta
   {
     "object": "page",
     "entry": [{
       "id": "<PAGE_ID>",
       "changes": [{
         "field": "leadgen",
         "value": {
           "leadgen_id":   "123456789",
           "page_id":      "<PAGE_ID>",
           "form_id":      "987654321",
           "adgroup_id":   "111111111",
           "ad_id":        "222222222",
           "created_time": 1716000000
         }
       }]
     }]
   }

4. Return HTTP 200 immediately; enqueue {leadgen_id, page_id, form_id, ad_id, tenant_id}

5. Worker calls Lead Retrieval API:
   GET /{leadgen_id}
      ?fields=id,created_time,ad_id,form_id,field_data,custom_disclaimer_responses
      &access_token={page_access_token}

6. Response:
   {
     "id": "123456789",
     "created_time": "2026-05-01T10:00:00+0000",
     "ad_id": "222222222",
     "form_id": "987654321",
     "field_data": [
       { "name": "email",                      "values": ["priya@example.com"] },
       { "name": "phone_number",               "values": ["+919876543210"] },
       { "name": "full_name",                  "values": ["Priya Sharma"] },
       { "name": "company_name",               "values": ["Acme Pvt Ltd"] },
       { "name": "job_title",                  "values": ["Founder"] },
       { "name": "which_city_are_you_from_0",  "values": ["Mumbai"] }
     ],
     "custom_disclaimer_responses": [
       { "checkbox_key": "gdpr_consent_0", "is_checked": true }
     ]
   }

7. Look up form field map for form_id → normalise field_data
8. Build NormalisedEvent → write lead + event → trigger Pipeline 1
```

### 3.2 Form Definition Pre-Fetch

The `field_data[].name` for custom questions is an internal key (e.g., `which_city_are_you_from_0`) — not the human-readable label. You cannot normalise reliably without knowing the mapping.

**When to fetch:** At connection time, enumerate all lead forms for the tenant's Page:

```
GET /{page_id}/leadgen_forms
   ?access_token={page_access_token}
   &fields=id,name,questions,status
```

Each question in the response:
```json
{
  "type":  "CUSTOM",
  "key":   "which_city_are_you_from_0",
  "label": "Which city are you from?"
}
```

Standard built-in fields have typed `type` values: `EMAIL`, `PHONE`, `FULL_NAME`, `COMPANY_NAME`, `JOB_TITLE`, `CITY`, `STATE`, `COUNTRY`, `ZIP_CODE`, `DATE_OF_BIRTH`, `GENDER`.

**Store the mapping** in a `lead_form_field_map` table:

```sql
CREATE TABLE lead_form_field_map (
  form_id     TEXT NOT NULL,
  field_key   TEXT NOT NULL,
  field_label TEXT,
  field_type  TEXT,          -- EMAIL | PHONE | FULL_NAME | CUSTOM | ...
  PRIMARY KEY (form_id, field_key)
);
```

Refresh this mapping whenever the tenant adds or modifies a lead form. Also refresh when a `leadgen` webhook arrives with a `form_id` not yet in the map (new form just created).

### 3.3 Normalisation Logic

```python
STANDARD_FIELD_MAP = {
    'email':        'email',
    'phone_number': 'phone',
    'full_name':    'full_name',
    'first_name':   'first_name',
    'last_name':    'last_name',
    'company_name': 'company',
    'job_title':    'job_title',
    'city':         'city',
    'state':        'state',
    'country':      'country',
    'zip_code':     'zip_code',
}

def normalise_lead_ad(field_data: list, form_id: str, db) -> dict:
    normalised = {}
    extra = {}

    form_map = db.fetch_form_map(form_id)  # {key: {label, type}}

    for field in field_data:
        key = field['name']
        value = field['values'][0] if len(field['values']) == 1 else field['values']

        if key in STANDARD_FIELD_MAP:
            normalised[STANDARD_FIELD_MAP[key]] = value
        elif key in form_map:
            extra[form_map[key]['label']] = value   # use human label as extra key
        else:
            extra[key] = value                       # fallback: raw key

    return {'mapped': normalised, 'extra_fields': extra}
```

### 3.4 Multi-Select Custom Questions

If a custom question allows multiple selections, `values` is a multi-element array:

```json
{ "name": "interested_products_0", "values": ["Product A", "Product C"] }
```

Store as a JSON array in `extra_fields`. Do not flatten to a comma-separated string — that breaks downstream parsing.

### 3.5 Custom Disclaimer Responses

Responses to optional custom disclaimer checkboxes do NOT appear in `field_data`. Include `custom_disclaimer_responses` explicitly in your retrieval call fields parameter. Store the result on the lead record for compliance purposes (e.g., GDPR consent tracking).

### 3.6 Race Condition — Fetching Too Early

If you call `GET /{leadgen_id}` within milliseconds of the webhook, the lead record may not yet be readable on Meta's side. Meta returns a generic error with code 100.

Handle with one delayed retry:

```python
async def fetch_lead_with_retry(leadgen_id, token, delay_seconds=3):
    try:
        return fetch_lead(leadgen_id, token)
    except MetaApiError as e:
        if e.code == 100:
            await asyncio.sleep(delay_seconds)
            return fetch_lead(leadgen_id, token)
        raise
```

This race condition is rare but occurs on high-traffic ad sets where Meta's internal fan-out is slower than your webhook processor.

### 3.7 Polling Fallback for Lead Ads

If a webhook is missed, poll leads directly from a form using `last_event_at` as the cursor:

```
GET /{form_id}/leads
   ?access_token={page_access_token}
   &fields=id,created_time,field_data,custom_disclaimer_responses
   &filtering=[{"field":"time_created","operator":"GREATER_THAN","value":{unix_timestamp}}]
```

Paginate using the `next` cursor in `paging.cursors`. Continue until no `next` cursor is returned.

**Enumerate all forms to poll:**
```
GET /{page_id}/leadgen_forms
   ?access_token={page_access_token}
   &fields=id,status
```

Filter for `status: ACTIVE`. Run this poll job per tenant per active form. Use `platform_event_id` dedup (Section 2.7) to ensure leads already written via webhook are not double-processed.

### 3.8 Attribution Data

The `adgroup_id` and `ad_id` fields in the webhook payload (and on the lead retrieval response) identify exactly which ad campaign and ad set generated the lead. Store these on the `event` record. This enables:
- Per-campaign lead quality reporting for the tenant
- Signal scoring: leads from high-intent campaigns get a higher intent signal weight

---

## 4. What Needs to Be Built — Implementation Checklist

| Component | Purpose | Notes |
|---|---|---|
| Facebook Login for Business config | WhatsApp Embedded Signup prerequisite | Done once in App Dashboard |
| Embedded Signup JS widget | Launch WhatsApp connection popup | Pass signed `state={tenant_id}` |
| `/oauth/callback` | Facebook + Instagram code → page tokens | Derive long-lived page tokens |
| `/embedded-signup/callback` | WhatsApp code → WABA token | Fetch phone_number_ids, register WABA webhook |
| `POST /{page_id}/subscribed_apps` call | Activate Facebook/Instagram webhooks per tenant | Called at connection time |
| Webhook endpoint (GET) | Challenge verification | Respond with `hub.challenge` as plain text |
| Webhook endpoint (POST) | HMAC validation → enqueue → HTTP 200 | Raw bytes validation before JSON parse |
| Webhook router | `entry[].id` / `phone_number_id` → tenant lookup | GIN index on `channel_connection.metadata` |
| Webhook worker | Event type dispatch → normalise → write → Pipeline 1 | Async; handles DM + leadgen + comment |
| Lead Retrieval API call | Fetch actual form field values | Include `custom_disclaimer_responses` in fields param |
| Race condition retry | Handle `code 100` on immediate retrieval | One retry after 3 seconds |
| Form definition pre-fetcher | Build `lead_form_field_map` per tenant per form | Run at connection time + on unknown form_id |
| `lead_form_field_map` table | Map `field_key` → `field_label` + `field_type` | Enables reliable custom field normalisation |
| Instagram token refresh job | Refresh 60-day Instagram tokens before expiry | Daily check; refresh when `expires_in` < 604800 |
| Polling fallback job | Catch missed webhooks per channel per tenant | Uses `last_event_at` as cursor |
| Stale connection monitor | Detect token revocation via silence | Alert on active connections with no events > 48h |

---

## Caveats and Gaps

- **Facebook Login for Business requires a different App configuration** than standard Facebook Login. If your app was built with standard Facebook Login, you need to add the Facebook Login for Business product separately. The Embedded Signup flow will not work without it.
- **WhatsApp sender profile picture is not available** via the official Cloud API. There is no workaround. Identity enrichment for WhatsApp leads relies on the phone number via Truecaller. See [[analyses/lead-enrichment-architecture]].
- **Custom lead form field names cannot be predicted** without the form definition pre-fetch. Do not attempt to normalise custom fields by guessing the `key` value — always use the `lead_form_field_map`.
- **Meta App Review must be complete** before any of this works for real tenant accounts. During development, all flows work for accounts with a developer/admin role on the Meta App. See [[analyses/meta-platform-api-deep-research]] Section 1.4 for timeline.
- **WhatsApp outbound messaging tiers:** New WABAs start at TIER_250 (250 unique recipients per 24h for outbound). This does not affect inbound event ingestion — receiving messages is unlimited. Becomes relevant when auto-response or outreach features are added post-MVP.

## Follow-up Questions

- Should the form definition pre-fetcher run on a schedule (e.g., nightly) to catch newly created forms, or only on unknown `form_id` in the webhook? Nightly sweep is safer for tenants who create forms outside of business hours.
- How do we handle `ad_id` attribution for Instagram Lead Ads vs Facebook Lead Ads — are both delivered through the Page-level `leadgen` webhook, or does Instagram have a separate subscription?
- Should we store `custom_disclaimer_responses` as a separate boolean field on the lead record (for GDPR compliance filtering) or as part of `extra_fields` JSONB?
- What is our plan for the WhatsApp TIER_250 onboarding limitation — should we document this as a known constraint in the tenant onboarding flow for the first 30 days?
