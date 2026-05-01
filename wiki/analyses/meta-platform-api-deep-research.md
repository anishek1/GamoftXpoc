---
type: analysis
question: "What are the precise technical specifications for integrating Meta platform APIs (Facebook Pages, Instagram Business, WhatsApp Cloud API) into a multi-tenant lead intelligence SaaS?"
date: 2026-05-01
tags: [meta, facebook, instagram, whatsapp, oauth, webhooks, lead-ads, api, channel-integration, multi-tenant]
sources_consulted:
  - "[[analyses/channel-integration-layer]]"
  - "[[analyses/lead-enrichment-architecture]]"
  - "Meta Permissions Reference: https://developers.facebook.com/docs/permissions/"
  - "Meta Access Token Guide: https://developers.facebook.com/docs/facebook-login/guides/access-tokens/"
  - "Long-Lived Token Guide: https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/"
  - "Business Verification: https://developers.facebook.com/docs/development/release/business-verification/"
  - "App Review: https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/app-review"
  - "Instagram App Review: https://developers.facebook.com/docs/instagram-platform/app-review/"
  - "Instagram API with Instagram Login: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/"
  - "Instagram Business Login: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/"
  - "Instagram OAuth Authorize: https://developers.facebook.com/docs/instagram-platform/reference/oauth-authorize/"
  - "Instagram User Profile API: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/user-profile/"
  - "Instagram Webhook Examples: https://developers.facebook.com/docs/instagram-platform/webhooks/examples/"
  - "Instagram Webhooks: https://developers.facebook.com/docs/instagram-platform/webhooks/"
  - "Instagram Messaging Feature Webhook: https://developers.facebook.com/docs/messenger-platform/instagram/features/webhook/"
  - "Messenger Webhook Reference: https://developers.facebook.com/docs/messenger-platform/reference/webhook-events/messages/"
  - "Pages Webhook Reference: https://developers.facebook.com/docs/graph-api/webhooks/reference/page/"
  - "Webhook Verification: https://developers.facebook.com/docs/graph-api/webhooks/getting-started"
  - "Leadgen Webhook: https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/"
  - "Lead Ads Guide: https://developers.facebook.com/docs/marketing-api/guides/lead-ads/"
  - "WhatsApp Cloud API Get Started: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
  - "WhatsApp Embedded Signup: https://developers.facebook.com/docs/whatsapp/embedded-signup/"
  - "WhatsApp WABA Management: https://developers.facebook.com/docs/whatsapp/embedded-signup/manage-accounts/"
  - "WhatsApp Business Accounts: https://developers.facebook.com/docs/whatsapp/overview/business-accounts/"
  - "WhatsApp Messaging Limits: https://developers.facebook.com/docs/whatsapp/messaging-limits/"
  - "WhatsApp System User Token: https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens/"
  - "System Users Business Management: https://developers.facebook.com/docs/business-management-apis/system-users/install-apps-and-generate-tokens/"
  - "Graph API Rate Limiting: https://developers.facebook.com/docs/graph-api/overview/rate-limiting/"
  - "Pages API: https://developers.facebook.com/docs/pages-api/"
status: COMPLETE
---

# Meta Platform API Deep Research — Lead Intelligence SaaS

**Question:** Precise technical specifications for Facebook Pages, Instagram Business, and WhatsApp Cloud API integration for a multi-tenant lead intelligence SaaS  
**Date:** 2026-05-01  
**Supersedes open items in:** [[analyses/channel-integration-layer]]

---

## 1. OAuth / Authorization Flow

### 1.1 Facebook Pages

**Required scopes for messaging + lead ads:**

| Permission | Purpose | Access Level |
|---|---|---|
| `pages_show_list` | List pages user manages | Advanced |
| `pages_manage_metadata` | Subscribe pages to webhooks | Advanced |
| `pages_messaging` | Send/receive messages via Messenger | Advanced |
| `pages_read_engagement` | Read page comments, reactions | Advanced |
| `leads_retrieval` | Retrieve lead form submissions | Advanced |
| `ads_management` | Required for leadgen webhook subscription | Advanced |

All of the above require **Advanced Access** which mandates both App Review and Business Verification. The dependency chain: `pages_messaging` → `pages_manage_metadata` → `pages_show_list`.

**Token types issued:**

1. **Short-lived User Access Token** — issued by the OAuth dialog. Valid ~1–2 hours. Obtained from `facebook.com/dialog/oauth`.
2. **Long-lived User Access Token** — exchanged server-side. Valid ~60 days. Derived via `GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={short_lived_token}`.
3. **Long-lived Page Access Token** — derived from the long-lived user token. **Does not expire under normal conditions.** Obtained via `GET /{app-scoped-user-id}/accounts?access_token={long_lived_user_token}`. Returns all pages the user manages; each page gets a distinct token.

**Non-expiring token derivation chain:**

```
facebook.com/dialog/oauth
   → short-lived User token (~1-2h)
        ↓ server-side exchange (app_secret required)
   → long-lived User token (~60 days)
        ↓ GET /{user_id}/accounts
   → long-lived Page Access Token  ←─ effectively permanent
```

**Conditions that invalidate a long-lived Page Access Token:**
- User changes their Facebook password
- User removes the app from their Facebook account
- User loses their admin role on the Page
- Meta invalidates sessions for security reasons (rare, unannounced)

These are the token failure conditions that must drive the `channel_connection.status = "expired"` flow in [[analyses/channel-integration-layer]].

**Non-expiring alternative — System User Token:**  
For programmatic server-side use without a human in the loop, a System User can be created in Meta Business Manager. System User tokens can be set to **never expire** (default when `set_token_expires_in_60_days` parameter is omitted). They can be assigned Admin or Employee roles and can hold Page permissions. This is the recommended approach for a SaaS platform's own Meta assets. For tenant-owned assets, the Page Access Token from the tenant's human account is the standard approach, because the tenant's business owns the Page.

---

### 1.2 Instagram Business

**Two API paths exist. Use only the newer one.**

| Path | Status | Scopes |
|---|---|---|
| Instagram API with Facebook Login | Legacy, still active | `instagram_basic`, `instagram_manage_messages`, `instagram_manage_comments` (Facebook-scoped) |
| **Instagram API with Instagram Login** | **Current — use this** | `instagram_business_basic`, `instagram_business_manage_messages`, `instagram_business_manage_comments`, `instagram_business_content_publish` |

**Scope deprecation event:** The old Business Login scope names (`business_basic`, `business_manage_messages`, `business_manage_comments`, `business_content_publish`) were **deprecated on January 27, 2025**. Apps still using them cannot call Instagram endpoints. Only the `instagram_business_*` prefixed names are valid.

**Scopes needed for lead intelligence (messaging only):**

| Permission | Required For |
|---|---|
| `instagram_business_basic` | Any Instagram API access; baseline permission |
| `instagram_business_manage_messages` | Reading and sending Instagram DMs |

**OAuth authorize endpoint:** `GET https://api.instagram.com/oauth/authorize`  
Parameters: `client_id`, `redirect_uri`, `response_type=code`, `scope=instagram_business_basic,instagram_business_manage_messages`

**Token types issued:**

1. **Authorization code** — returned to `redirect_uri` after user consent. Valid 1 hour, single-use.
2. **Short-lived Instagram User Access Token** — exchanged from the authorization code via `POST https://api.instagram.com/oauth/access_token`. Valid ~1 hour.
3. **Long-lived Instagram User Access Token** — exchanged server-side via `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_id={app_id}&client_secret={app_secret}&access_token={short_lived_token}`. Valid **60 days**.

**Key difference from Facebook:** Instagram long-lived User tokens are valid 60 days and must be refreshed. There is no equivalent of the Facebook "long-lived Page Token that never expires" for Instagram Login path. The token must be refreshed before it expires.

**Refresh:** `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token={long_lived_token}` — resets the 60-day window. Can only be called while the token is still valid (not after it has expired).

**Token refresh automation:** The long-lived token response includes an `expires_in` field (seconds until expiry). A background job must track this and call `/refresh_access_token` before the token expires. Recommended trigger: when `expires_in` < 604800 (7 days remaining). If the token expires before refresh, the tenant must re-complete the OAuth flow. Schedule the refresh job to run daily and check all Instagram tokens in `channel_connection` with status `active`.

**Does Instagram with Instagram Login require a linked Facebook Page?** No. This is a key distinction. Instagram API with Instagram Login allows professionals to manage their Instagram presence directly without a linked Facebook Page. The Facebook Login path requires a linked Page. Build against Instagram Login path.

---

### 1.3 WhatsApp Business Cloud API

**Architecture:** WhatsApp uses a different model from Facebook/Instagram. The central entity is the **WABA (WhatsApp Business Account)** — a business's identity on the WhatsApp platform. A WABA contains one or more **phone numbers**, each identified by a `phone_number_id`. Your Meta App does not "own" the WABA; it is **shared** with your app by the business owner via the Embedded Signup flow.

**Scopes required for the OAuth configuration of Embedded Signup:**

| Permission | Purpose |
|---|---|
| `whatsapp_business_management` | Manage WABA settings, phone numbers, templates |
| `whatsapp_business_messaging` | Send and receive messages |

Both require App Review and Business Verification.

**The Embedded Signup flow (correct approach for multi-tenant SaaS):**

```
Tenant: Settings → "Connect WhatsApp"
     ↓
Your app launches the Meta Embedded Signup flow
  (configured with Facebook Login for Business + WhatsApp scopes)
     ↓
Tenant logs into their Facebook Business account
     ↓
Tenant selects or creates a WABA
Tenant selects or registers a phone number
     ↓
Flow completes → returns:
  code: {exchangeable_short_lived_code}
  WABA_id: {waba_id}
  phone_number_id: {phone_number_id}
     ↓
Your backend: POST /oauth/access_token with the code
     → Returns a Business Integration System User access token
     ↓
Store token in secrets manager
Register webhook on WABA for messages field
```

**Business Integration System User access token:** This is the correct token type for a SaaS platform receiving tenant messages server-side. It represents the tenant's WABA, not a human user. It is **non-expiring by default** (no time-based expiry). It is the per-tenant equivalent of a System User token.

**Fetching all WABAs shared with your app:**
```
GET /{business_manager_id}/client_whatsapp_business_accounts
   ?access_token={your_system_user_token}
```
Returns all WABAs shared with your Business Manager. Use `granular_scopes` in the Debug Token response to get the WABA IDs that granted specific permissions.

**phone_number_id vs WABA_id:**
- One WABA can have multiple phone numbers.
- Each phone number has a unique `phone_number_id`.
- Messages are sent and received at the `phone_number_id` level.
- Webhook `metadata.phone_number_id` tells you which phone number (and therefore which tenant) received a message.
- To get all phone numbers for a WABA: `GET /{waba_id}/phone_numbers`.

---

### 1.4 Meta Business Verification and App Review

**Business Verification:**
- Completed in Business Manager → App Dashboard → Settings → Basic → Verification
- Required for: any app requesting Advanced Access permissions that will be used by people outside your organization
- Process: connect app to a Business, verify the business via Meta Business Manager (document submission)
- Timeline: varies; Meta documentation says approximately 5 days but recommends allowing up to 60 days if additional information is needed

**App Review:**
- Required for: any permission or feature that needs Advanced Access and will be used by accounts your team does not own
- Submission requirements:
  1. Loadable, testable app with visible login button
  2. Detailed use case description per permission
  3. Step-by-step testing instructions for Meta's reviewers
  4. Screencast in English with captions demonstrating each permission's usage
  5. At least one successful API call per permission made within 30 days before submission
  6. Complete app settings: icon, privacy policy URL, app category, support email
- Timeline: **2–7 days** for a clean first submission; plan for **2 weeks minimum buffer** before target launch to allow for revision cycles
- Outcome: Approved permissions become available for all users; unapproved permissions remain available only to users with a role on the app itself

**Access levels:**
- **Standard Access:** Default for development/testing. Only works for accounts with a role on the app (your team). No App Review required.
- **Advanced Access:** Required to use the app with your customers' accounts. Requires App Review + Business Verification.

**Permissions requiring App Review for the lead intelligence use case:**

| Surface | Permissions requiring Advanced Access + App Review |
|---|---|
| Facebook Pages | `pages_show_list`, `pages_manage_metadata`, `pages_messaging`, `pages_read_engagement`, `leads_retrieval`, `ads_management` |
| Instagram (Instagram Login path) | `instagram_business_basic`, `instagram_business_manage_messages` |
| WhatsApp | `whatsapp_business_management`, `whatsapp_business_messaging` |

---

## 2. Webhook Subscriptions

### 2.1 Webhook Verification (All Platforms)

Meta uses the same challenge-response pattern for all surfaces:

**Setup-time verification (GET request):**
```
GET https://your-endpoint.com/webhook
  ?hub.mode=subscribe
  &hub.challenge=1158201444
  &hub.verify_token=myVerifyToken
```
Your endpoint must:
1. Check that `hub.verify_token` matches your configured value
2. Write the `hub.challenge` value as the **plain text HTTP response body** and return HTTP 200. The response body must contain only the challenge value — no JSON wrapper, no quotes. Example: if `hub.challenge=1158201444`, the response body is `1158201444` and the status is 200.

**Runtime signature validation (every POST):**
- Meta signs every POST payload with HMAC-SHA256 using your app secret
- Signature is in the `X-Hub-Signature-256` header, formatted as `sha256={signature}`
- Validate: generate `HMAC-SHA256(app_secret, request_body)`, compare to the value after `sha256=`
- Reject any payload where signatures do not match

**Two-tier subscription model (applies to all surfaces):**
Before per-page or per-account webhook subscriptions can be registered, the app itself must be configured with a webhook URL and verify token at the app level (App Dashboard → Add Product → Webhooks). This app-level configuration must be completed first. Only then can per-page or per-WABA subscriptions succeed. If webhook events stop arriving, check both tiers: (1) app-level webhook product configuration, and (2) per-resource subscription via the API call.

---

### 2.2 Facebook Pages Webhook Fields

Subscribe a page: `POST /{page_id}/subscribed_apps?subscribed_fields={fields}&access_token={page_access_token}`  
Requires: Page access token from someone with CREATE_CONTENT, MANAGE, or MODERATE task on the Page.

| Field | What it delivers | Key permissions |
|---|---|---|
| `messages` | Inbound Messenger DMs to the Page | `pages_messaging`, `pages_manage_metadata` |
| `messaging_postbacks` | Button postback clicks | `pages_manage_metadata` |
| `messaging_optins` | Notification opt-ins, one-time notification consents | `pages_manage_metadata` |
| `messaging_handovers` | Thread control transfers between Handover Protocol apps | `pages_manage_metadata` |
| `messaging_policy_enforcement` | Policy violation notifications | `pages_manage_metadata` |
| `message_deliveries` | Delivery confirmations | `pages_manage_metadata` |
| `message_reads` | Read receipts | `pages_manage_metadata` |
| `feed` | Page feed changes: posts, comments, reactions, shares | `pages_manage_metadata` |
| `leadgen` | Lead Ad form submission events | `pages_manage_metadata`, `leads_retrieval`, `ads_management` |

**Facebook Messenger message webhook payload:**
```json
{
  "object": "page",
  "entry": [{
    "id": "<PAGE_ID>",
    "time": 1583173667623,
    "messaging": [{
      "sender":    { "id": "<PSID>" },
      "recipient": { "id": "<PAGE_ID>" },
      "timestamp": 1583173666767,
      "message": {
        "mid":  "m_toDnmD...",
        "text": "Hello, I'm interested in your product",
        "attachments": [{
          "type": "fallback",
          "payload": { "url": "<URL>", "title": "<TITLE>" }
        }]
      }
    }]
  }]
}
```

**What is in the payload:** PSID (sender ID), page ID (recipient), timestamp, message ID, text, attachment URLs.  
**What is NOT in the payload:** sender name, profile picture, locale, timezone. These require a follow-up Graph API call.

**Follow-up call for Facebook sender profile:**
```
GET /{psid}?fields=name,first_name,last_name,profile_pic
   &access_token={page_access_token}
```
Returns: `name`, `first_name`, `last_name`, `profile_pic` (URL). Note: profile data availability depends on the user's privacy settings and whether they have blocked the business.

---

### 2.3 Instagram Webhook Fields

Instagram webhooks use `object: "instagram"` in the payload.  
Subscribe: Instagram webhooks are configured in the App Dashboard Webhooks section, linking to a verified Instagram Professional account.

| Field | What it delivers |
|---|---|
| `messages` | Direct messages to the Instagram Professional account |
| `message_echoes` | Echo of messages sent by the business |
| `message_reactions` | Reactions to messages |
| `messaging_handover` | Handover Protocol events |
| `messaging_optins` | User opt-ins |
| `messaging_postbacks` | Postback interactions |
| `messaging_referral` | Referral data |
| `messaging_seen` | Read receipts |
| `comments` | Comments on posts (including mentions in comments) |
| `live_comments` | Comments during live broadcasts |
| `story_insights` | Metrics for the first 24 hours before story expires |

**Instagram DM webhook payload:**
```json
{
  "object": "instagram",
  "entry": [{
    "id": "<IGID>",
    "time": 1569262486134,
    "messaging": [{
      "sender":    { "id": "<IGSID>" },
      "recipient": { "id": "<IGID>" },
      "timestamp": 1569262485349,
      "message": {
        "mid":  "MESSAGE-ID",
        "text": "MESSAGE-TEXT",
        "attachments": [{
          "type":    "image",
          "payload": { "url": "<LINK>" }
        }]
      }
    }]
  }]
}
```

**What is in the payload:** IGSID (sender's Instagram-scoped ID), recipient IGID, timestamp, message ID, text, attachment URLs.  
**What is NOT in the payload:** username, name, profile picture, follower count. These require a follow-up User Profile API call.

**Instagram comment webhook payload** (field: `comments`):
```json
{
  "field": "comments",
  "value": {
    "from": { "id": "<COMMENTER_ID>", "username": "<USERNAME>" },
    "text":     "<COMMENT_TEXT>",
    "media":    { "id": "<MEDIA_ID>", "media_product_type": "FEED" },
    "comment_id": "<COMMENT_ID>",
    "parent_id":  "<PARENT_COMMENT_ID>"
  }
}
```
Note: the `comments` field DOES include `username` directly. The DM `messages` field does NOT.

**Story mention handling:**
- Instagram Login path: story mentions arrive within `comments` notifications
- Facebook Login (legacy) path: separate `mentions` field with `value.media_id`

**Follow-up call for Instagram sender profile (via User Profile API):**
```
GET https://graph.instagram.com/v25.0/<INSTAGRAM_SCOPED_USER_ID>
   ?fields=name,username,profile_pic,follower_count,
           is_verified_user,is_user_follow_business,is_business_follow_user
   &access_token={instagram_user_access_token}
```

Available fields:

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name; nullable |
| `username` | string | Instagram handle |
| `profile_pic` | URL | Expires in days; nullable |
| `follower_count` | integer | |
| `is_verified_user` | boolean | Blue checkmark status |
| `is_user_follow_business` | boolean | Does sender follow your account? |
| `is_business_follow_user` | boolean | Does your account follow sender? |

**Consent requirement:** This call only works after the user has initiated a message to your business, clicked an icebreaker, or used a persistent menu. You cannot proactively query strangers' profiles.

**Known limitation — username from IGSID:** Querying `?fields=username` on an IGSID using the IGBusinessScopedID node type returns an error in some API versions. The documented workaround is to use the Conversations API: `GET /{ig_id}/conversations?user_id={igsid}&fields=participants` to retrieve thread participants including username. The User Profile API endpoint above is the primary supported path for the `instagram_business_*` scopes.

**Required permissions for User Profile API:**
- `instagram_business_basic`
- `instagram_business_manage_messages`

---

### 2.4 WhatsApp Cloud API Webhook Events

**Subscribe:** Configure webhook URL in the App Dashboard, subscribe to the `messages` field on your WABA.

**Available webhook fields for WhatsApp:**

| Field | What it delivers |
|---|---|
| `messages` | Inbound messages AND message status updates (sent, delivered, read) |

All inbound event types arrive under the single `messages` subscription field. The `type` inside the payload distinguishes them.

**Inbound message webhook payload:**
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "<WABA_ID>",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "15551797781",
          "phone_number_id": "7794189252778687"
        },
        "contacts": [{
          "profile": { "name": "Jessica Laverdetman" },
          "wa_id": "13557825698"
        }],
        "messages": [{
          "from":      "17863559966",
          "id":        "wamid.HBgL...",
          "timestamp": "1758254144",
          "text":      { "body": "Hi!" },
          "type":      "text"
        }]
      },
      "field": "messages"
    }]
  }]
}
```

**Message status update payload (same `messages` field):**
```json
{
  "statuses": [{
    "id":           "wamid.HBgL...",
    "status":       "delivered",
    "timestamp":    "1758254200",
    "recipient_id": "13557825698",
    "conversation": { "id": "<CONV_ID>", "origin": { "type": "service" } },
    "pricing":      { "billable": true, "pricing_model": "CBP", "category": "service" }
  }]
}
```

Status values: `sent`, `delivered`, `read`, `failed`.

**Key field inventory for WhatsApp inbound:**

| Field path | Value | Notes |
|---|---|---|
| `metadata.phone_number_id` | Your tenant's phone number ID | Use for multi-tenant routing |
| `metadata.display_phone_number` | Human-readable phone number | |
| `contacts[].wa_id` | Sender's WhatsApp ID (phone number) | Primary contact identifier |
| `contacts[].profile.name` | Sender's WhatsApp display name | From sender's own WhatsApp profile |
| `messages[].from` | Sender phone number | Same value as `wa_id` |
| `messages[].id` | Message ID (wamid format) | For dedup, delivery tracking |
| `messages[].timestamp` | Unix timestamp | |
| `messages[].type` | `text`, `image`, `audio`, `video`, `document`, `location`, `contacts`, `interactive`, `button`, `order`, `system`, `unknown` | |
| `messages[].text.body` | Message text (for `type: "text"`) | |

**Contact profile data available without any follow-up call:**
- `wa_id` (phone number in E.164 format) — always present
- `contacts[].profile.name` — sender's WhatsApp display name — present when the sender has a display name set

**Contact profile data NOT available in WhatsApp Cloud API:**
- Profile picture of the contact: **Not available via official Meta WhatsApp Cloud API.** There is no official endpoint to retrieve a contact's profile photo. The Business Profile API (`GET /{phone_number_id}/whatsapp_business_profile`) returns your business's own profile fields (`about`, `address`, `description`, `email`, `profile_picture_url`, `websites`, `vertical`) — not the contact's.
- About/status text of the contact: **Not available.**

This is a documented limitation of the Cloud API. Third-party providers (Whapi, WOZTELL) offer unofficial workarounds, but these are against Meta's Terms of Service and cannot be used in a production SaaS.

---

## 3. Data Automatically Available Per Event

### 3.1 Facebook Messenger DM

| Data point | In webhook payload | Requires follow-up call |
|---|---|---|
| Sender PSID | Yes — `sender.id` | — |
| Recipient page ID | Yes — `recipient.id` | — |
| Message text | Yes — `message.text` | — |
| Attachment URLs | Yes — `message.attachments[].payload.url` | — |
| Message ID | Yes — `message.mid` | — |
| Timestamp | Yes — `timestamp` | — |
| Sender name | No | `GET /{psid}?fields=name` with page token |
| Sender profile picture | No | `GET /{psid}?fields=profile_pic` with page token |
| Sender locale/timezone | No | `GET /{psid}?fields=locale,timezone` with page token |

### 3.2 Instagram DM

| Data point | In webhook payload | Requires follow-up call |
|---|---|---|
| Sender IGSID | Yes — `messaging[].sender.id` | — |
| Recipient IGID | Yes — `messaging[].recipient.id` | — |
| Message text | Yes — `message.text` | — |
| Attachment URLs | Yes — `message.attachments[].payload.url` | — |
| Message ID | Yes — `message.mid` | — |
| Timestamp | Yes — `timestamp` | — |
| Sender username | No (not in DM payload) | User Profile API call |
| Sender display name | No | User Profile API call |
| Sender profile picture | No | User Profile API call (expires in days) |
| Follower count | No | User Profile API call |
| Verification status | No | User Profile API call |
| Follow relationship | No | User Profile API call |

**Note on username in comments:** The `comments` webhook field DOES include `from.username` directly. Only the `messages` (DM) field lacks it.

**Can you get profile picture without the sender messaging you first?** No. The User Profile API requires user consent, which is established only when they initiate contact with the business.

### 3.3 WhatsApp Inbound Message

| Data point | In webhook payload | Requires follow-up call |
|---|---|---|
| Sender phone number (wa_id) | Yes — `contacts[].wa_id` | — |
| Sender display name | Yes — `contacts[].profile.name` (if set) | — |
| Message text | Yes — `messages[].text.body` | — |
| Message type | Yes — `messages[].type` | — |
| Message ID | Yes — `messages[].id` | — |
| Timestamp | Yes — `messages[].timestamp` | — |
| Phone number ID (which tenant) | Yes — `metadata.phone_number_id` | — |
| Sender profile picture | No | **Not available in Cloud API** |
| Sender about/bio text | No | **Not available in Cloud API** |
| Additional contact lookup | N/A | No official endpoint |

### 3.4 Meta Lead Ads (leadgen webhook + Lead Retrieval API)

**What arrives in the leadgen webhook:**
```json
{
  "object": "page",
  "entry": [{
    "id": 153125381133,
    "time": 1438292065,
    "changes": [{
      "field": "leadgen",
      "value": {
        "leadgen_id":   "123123123123",
        "page_id":      "123123123",
        "form_id":      "12312312312",
        "adgroup_id":   "12312312312",
        "ad_id":        "12312312312",
        "created_time": 1440120384
      }
    }]
  }]
}
```

The webhook carries **only IDs — no actual lead form field values**. The lead data must be fetched separately.

**Lead Retrieval API — fetching the actual lead:**
```
GET /{leadgen_id}
   ?access_token={page_access_token}
```

**Response structure:**
```json
{
  "id":           "123123123123",
  "created_time": "2024-01-15T10:30:00+0000",
  "ad_id":        "12312312312",
  "form_id":      "12312312312",
  "field_data": [
    { "name": "email",        "values": ["user@example.com"] },
    { "name": "phone_number", "values": ["+919876543210"] },
    { "name": "full_name",    "values": ["Priya Sharma"] },
    { "name": "company_name", "values": ["Acme Corp"] },
    { "name": "job_title",    "values": ["Marketing Manager"] },
    { "name": "city",         "values": ["Mumbai"] }
  ]
}
```

**Standard built-in field names** (set by Meta, used in form builder):

The following field names are well-documented in Meta's developer documentation and confirmed in fetched API responses. Fields marked [doc-confirmed] were present in documentation retrieved during this research. Fields marked [training] were derived from training knowledge and should be verified against your own form definition via `GET /{form_id}?fields=questions` before relying on them in production normalization logic.

To enumerate all fields for a specific form definitively: `GET /{form_id}?fields=questions&access_token={page_access_token}`.

| Field name | Data | Verification |
|---|---|---|
| `email` | Email address | doc-confirmed |
| `phone_number` | Phone number | doc-confirmed |
| `full_name` | Full name | doc-confirmed |
| `first_name` | First name | doc-confirmed |
| `last_name` | Last name | doc-confirmed |
| `date_of_birth` | DOB | doc-confirmed |
| `gender` | Gender | doc-confirmed |
| `city` | City | doc-confirmed |
| `state` | State/province | doc-confirmed |
| `country` | Country | doc-confirmed |
| `zip_code` | Postal code | doc-confirmed |
| `street_address` | Street | doc-confirmed |
| `company_name` | Company | doc-confirmed |
| `job_title` | Job title | doc-confirmed |
| `work_email` | Work email | [training] |
| `military_status` | Military status | [training] |
| `marital_status` | Marital status | [training] |

**Custom fields:** Form owners can add custom questions with any label. These appear in `field_data` with whatever `name` the form creator assigned. There is no way to predict custom field names without reading the form definition first (`GET /{form_id}?fields=questions`).

**Note on custom disclaimer checkboxes:** Responses to optional custom disclaimer checkboxes are NOT in `field_data`. Use the `custom_disclaimer_responses` field on the lead object if that data is needed.

**Permissions required to call Lead Retrieval API:**
- `leads_retrieval`
- `pages_manage_metadata`
- `pages_show_list`
- `pages_read_engagement`
- `ads_management`

Requires a Page access token from someone with ADVERTISE task permission on the Page.

**Rate limits for Lead Retrieval API:** Meta does not publish a specific rate limit for the leadgen retrieval endpoint. It falls under the standard Graph API Business Use Case rate limits for page tokens: `4800 * number_of_engaged_users` calls per 24 hours. In practice, for a lead intelligence SaaS, fetching one lead record per webhook event is well within limits. Best practice: fetch within seconds of the webhook to minimize latency.

---

## 4. Meta Lead Ads — Complete Picture

### 4.1 End-to-End Flow

```
User fills Facebook/Instagram Lead Ad form
    ↓
Meta fires leadgen webhook to your endpoint
  Payload: leadgen_id, page_id, form_id, ad_id, created_time
    ↓
Your backend receives webhook immediately
    ↓
GET /{leadgen_id}?access_token={page_token}
    ↓
Response: field_data[] with name/values pairs
    ↓
NormalisedEvent.form_response = { email: "...", phone: "...", ... }
    ↓
Pipeline 1 triggered
```

### 4.2 Webhook Subscription for Lead Ads

Subscribe the page to the `leadgen` field:
```
POST /{page_id}/subscribed_apps
   ?subscribed_fields=leadgen
   &access_token={page_access_token}
```

Also requires your app to have a subscription to the `leadgen` webhook object at the app level (configured in App Dashboard → Webhooks).

### 4.3 Time Window

There is no documented hard expiry on fetching a lead via the Lead Retrieval API. Meta does not publish a data retention deadline after which `GET /{leadgen_id}` stops returning data.

**Important clarification on "90 days":** The 90-day figure that appears in Meta documentation refers to the **rate limit calculation window** — specifically, engaged users for BUC rate limit purposes are counted over the past 90 days. It is not a statement about when lead records are deleted or become unretrievable.

**Practical guidance:** Fetch the lead record within the same request cycle as the webhook event. Do not rely on the lead record persisting indefinitely; store all retrieved lead data in your own datastore immediately. This also minimizes pipeline latency. If a webhook is missed or processing fails, the polling fallback should re-fetch any unprocessed leads from the platform API within hours, not days.

---

## 5. WhatsApp Business Cloud API Specifics

### 5.1 WABA Architecture

```
Meta App
  └─ linked to Business Manager
       └─ multiple customer WABAs shared via Embedded Signup
            └─ each WABA has 1+ phone numbers
                 └─ each phone number has a phone_number_id
```

One Meta App can serve **unlimited tenant WABAs**. Each WABA is a separate business account with its own `phone_number_id`(s). The `phone_number_id` in webhook `metadata` is how you determine which tenant the message belongs to — map it to `channel_connection.metadata.phone_number_id` at webhook receipt time.

### 5.2 24-Hour Messaging Window

The window governs what **you can send**, not what you receive. Inbound messages are not rate-limited.

**Customer Service Window rules:**
- Triggered when: a WhatsApp user messages your business OR calls your business
- Window duration: **24 hours** from last user-initiated message
- While open: you can send **any type of message** (free text, media, templates)
- Window closed: you can ONLY send approved **Template Messages**

**Free Entry Point (FEP) Window:**
- Triggered when: user messages via Click-to-WhatsApp Ad or Facebook Page CTA
- If you respond within 24h: a **72-hour** FEP window opens; all messages in this window are free

**Impact on event ingestion for lead intelligence:**
- **Inbound message events are always received** regardless of window state — receiving is not limited
- Window state matters only when you want to send follow-up messages from the system
- At MVP (receive-only), window rules are not a blocker; they become relevant when auto-response or outreach features are added

### 5.3 Token for Multi-Tenant WhatsApp

The Business Integration System User access token (obtained by exchanging the Embedded Signup code) is the correct token per tenant WABA. Store it at `{tenant_id}/whatsapp/{phone_number_id}/access_token` in secrets manager. Each tenant gets a separate token.

### 5.4 Profile Data Available for WhatsApp Contacts

Available from webhook payload itself (no API call):
- `wa_id` — sender's phone number (E.164 format, e.g., `917890123456`)
- `contacts[].profile.name` — sender's WhatsApp display name (what they set in their WhatsApp settings; not always present)

Not available via official Cloud API:
- Profile picture of the contact (sender)
- About/bio text of the contact (sender)

The Cloud API has a Business Profile endpoint for **your own** business profile fields. There is no official API to read a contact's profile photo or about text. This is a deliberate privacy restriction by Meta.

---

## 6. Rate Limits and Quotas

### 6.1 Graph API Rate Limits

| Token type | Rate limit model | Limit |
|---|---|---|
| User Access Token | Platform Rate Limit | `200 * number_of_daily_active_users` calls per hour (app-wide) |
| App Access Token | Platform Rate Limit | `200 * number_of_daily_active_users` calls per hour |
| Page Access Token | Business Use Case (BUC) Rate Limit | `4800 * number_of_engaged_users` calls per 24 hours |
| System User Token | Business Use Case (BUC) Rate Limit | Same as page token for page-related calls |

For a lead intelligence SaaS, all Meta API calls (lead retrieval, user profile lookup, webhook subscription) use Page Access Tokens or equivalent BUC tokens. The `4800 * engaged_users` formula means limit scales with tenant activity.

### 6.2 WhatsApp Business Management API Rate Limits

| Account status | Limit |
|---|---|
| New / default | 200 requests/hour |
| Standard | Up to 5,000 requests/hour |

These apply to WABA management calls (listing phone numbers, managing templates, etc.) — not to inbound message receipt.

### 6.3 WhatsApp Cloud API — Outbound Messaging Tiers

These are **outbound** tiers (sending messages), which affects how you respond to leads:

| Tier | Limit |
|---|---|
| TIER_250 | 250 unique recipients per 24h (starting tier for new WABAs) |
| TIER_1K | 1,000 unique recipients per 24h |
| TIER_10K | 10,000 unique recipients per 24h |
| TIER_100K | 100,000 unique recipients per 24h |
| Unlimited | No limit |

Check current tier: `GET /{phone_number_id}?fields=whatsapp_business_manager_messaging_limit`.  
Maximum send throughput on Cloud API: **1,000 messages per second**.

**Receiving messages:** Inbound message webhooks have no documented rate limit — you receive every message the user sends.

### 6.4 Webhook Delivery

Meta does not publish a rate limit for webhook delivery. Webhooks are best-effort; Meta will retry on delivery failure. Use HMAC validation (described above) to authenticate every delivery.

---

## 7. Multi-Tenant Considerations

### 7.1 One Meta App, Multiple Tenants

Yes — a single Meta App can serve unlimited business tenants. Each tenant completes the OAuth / Embedded Signup flow against your single app. Your app receives tokens per tenant, manages per-tenant webhook subscriptions, and routes incoming events to the correct tenant using:

- **Facebook/Instagram:** `entry[].id` (Page ID or IGID) → maps to `channel_connection.metadata.page_id`
- **WhatsApp:** `metadata.phone_number_id` → maps to `channel_connection.metadata.phone_number_id`

### 7.2 System User vs Page Access Token for Tenants

| Token type | When to use |
|---|---|
| **Page Access Token (from human)** | When the tenant's human business owner grants access via OAuth. Standard for Facebook Pages + Instagram. The tenant owns the Page; your app acts on their behalf. |
| **System User Token (your Business Manager)** | For assets your organization owns (your own test pages, your company's own Meta assets). |
| **Business Integration System User Token** | For WhatsApp WABA access obtained via Embedded Signup. Represents the tenant's WABA shared with your app. Non-expiring. |

For Facebook Pages and Instagram, use the **long-lived Page Access Token derived from the tenant's human OAuth flow**. For WhatsApp, use the **Business Integration System User Token** from Embedded Signup.

Do not create System Users in your Business Manager for tenant-owned assets; this would give your app direct ownership over their business data, which is both a ToS violation and a security risk for the tenant.

### 7.3 Token Revocation Handling

When a human business owner revokes access (removes your app from their Facebook account, or disconnects in WhatsApp):

**Detection signals:**
- Graph API returns HTTP 401 with error code `190` (invalid token) or `102` (session invalidated)
- Meta can also send a `deauthorize_callback_url` POST to a URL you configure in your app settings — provides proactive notification before you make a failing API call

**Response protocol (matches [[analyses/channel-integration-layer]] token lifecycle):**
1. Catch 401 → update `channel_connection.status = "revoked"`
2. Create `alert_incident` → notify tenant admin
3. Stop polling / stop processing webhooks for that connection
4. Tenant must re-complete OAuth flow to restore connection

**Webhook subscriptions after revocation:** Webhook subscriptions on a Page are associated with the app-Page subscription, not the individual human's token. If the person who granted access removes the app, the Page subscription is also removed. Your app will stop receiving webhooks for that page.

---

## 8. Caveats and Gaps

1. **Instagram DM username availability:** The documented User Profile API returns `username` via `GET https://graph.instagram.com/v25.0/{IGSID}`. However, community reports indicate that querying `username` on the `IGBusinessScopedID` node can fail. Use the Conversations API participants path as fallback. This should be tested in your app before relying on it.

2. **Instagram token refresh automation:** Instagram long-lived tokens expire in 60 days and must be refreshed. This requires a background job in the channel integration layer to refresh tokens before they expire. There is no equivalent of the non-expiring Facebook Page token for Instagram.

3. **Lead Ads field names are form-defined:** Standard field names (email, phone_number) are predictable. Custom fields are named by the form creator and cannot be predicted without a form definition lookup. For normalization, your `NormalisedEvent` build step should attempt to map well-known standard names and store unknown names in a raw `extra_fields` JSONB column.

4. **WhatsApp Embedded Signup requires Facebook Login for Business setup:** Your Meta App must be configured with Facebook Login for Business (not standard Facebook Login) to support the Embedded Signup flow. This is a different app product configuration.

5. **App Review is per-permission, not per-app:** You can submit individual permissions for review. If one permission is rejected, others can still be approved. Plan to submit all lead intelligence permissions in one batch but be prepared to have sub-batches approved at different times.

6. **WhatsApp sender name reliability:** `contacts[].profile.name` in webhook payloads is the sender's self-reported WhatsApp display name, not their legal name. Do not treat it as a reliable identity field. Cross-validate with Truecaller or form submission data where available.

7. **Meta's API surface is actively changing:** The Instagram scope deprecation (Jan 27, 2025) is an example of breaking changes without long notice windows. Monitor the [Meta Platform Changelog](https://developers.facebook.com/docs/changelog/) and subscribe to developer email updates.

---

## Follow-up Questions

- For Facebook DM sender profile enrichment, how do we handle users with strict privacy settings who return empty/null profile fields?
- Should we attempt the Conversations API participants workaround for Instagram username, or rely solely on the User Profile API?
- How does the WhatsApp message credit tier (TIER_250 for new WABAs) affect new tenant onboarding — should we document this as a known limitation for tenants in the first 30 days?
- Should we store the `form_id` from leadgen webhooks to pre-fetch form definitions and build a field name mapping table per tenant per form? (This would resolve the [training]-tagged Lead Form fields above and provide a reliable normalization basis per tenant.)
