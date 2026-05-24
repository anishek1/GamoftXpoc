---
type: analysis
question: "What is the complete REST API contract for the Lead Intelligence Engine — every endpoint, its roles, request shape, and response shape?"
date: 2026-05-20
tags: [api, rest, contract, endpoints, openapi, auth, rbac, webhooks, leads, pipeline, onboarding]
sources_consulted:
  - "[[analyses/security-planning]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/onboarding-flow-stage-map]]"
  - "[[analyses/onboarding-flow-readiness]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/llm-io-contract]]"
status: COMPLETE
---

# API Contract — Lead Intelligence Engine

**Question:** What is the complete REST API contract — every endpoint, its roles, request shape, and response shape?
**Date:** 2026-05-20

This document is the authoritative REST API reference. It defines what endpoints exist, who can call them, and what the request/response shapes look like. It does not define implementation — refer to the referenced analysis docs for internal logic.

---

## Plain-English Summary

**Why this exists:** Developers building a frontend, integrating a CRM, or wiring up the backend services need to know exactly what the API looks like before writing any code. This document answers: "What endpoint do I call?", "What do I send?", "What do I get back?", and "Who is allowed to call it?"

**How auth works:** Every request (except inbound webhooks) requires a Clerk JWT in the `Authorization` header. The JWT carries `org_id` (= `tenant_id`) and `org_role` (= one of `admin`, `team_lead`, `salesperson`, `viewer`). The API middleware validates the token, sets the Postgres RLS context, and enforces the role check. See [[analyses/security-planning]] §1.1–1.3 for the full auth model.

---

## Conventions

### Base URL
```
https://api.{domain}/v1/
```
URL path versioning. All endpoints are prefixed `/v1/`.

### Authentication

All endpoints except inbound webhooks require:
```
Authorization: Bearer <clerk_jwt>
```
JWT contains: `sub` (user_id), `org_id` (tenant_id), `org_role` (role).

Webhook endpoints use HMAC-SHA256 signature validation instead (see Webhooks group).

### Roles

| Role | Who | Scope |
|---|---|---|
| `admin` | Gamoft team only | Cross-tenant |
| `team_lead` | One or more per tenant | Own tenant only |
| `salesperson` | Sales reps | Own assigned leads only |
| `viewer` | Read-only stakeholders | Aggregated metrics only |

### Standard Error Response

All errors return:
```json
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

Common HTTP codes: `400` (bad request), `401` (missing/invalid token), `403` (forbidden — wrong role), `404` (not found), `422` (validation error), `429` (rate limit), `500` (server error).

### Async Responses

Operations that trigger background jobs (Pipeline 2, Pipeline 1 rescore) return immediately with a job reference:
```json
{
  "job_id": "uuid",
  "status": "queued"
}
```
Poll `GET /v1/pipeline/runs/{run_id}` for status.

### Pagination

List endpoints use cursor-based pagination:
```
GET /v1/leads?limit=50&cursor=<opaque_string>
```
Response includes `next_cursor: string | null`.

---

## Endpoint Groups

---

## 1. Tenant Onboarding

Covers the 5-stage onboarding journey. See [[analyses/onboarding-flow-stage-map]] for stage detail.

---

#### POST /v1/tenants
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Create a new tenant record (Stage 2 of onboarding).

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | Yes | Display name of the organization |
| `slug` | string | Yes | Unique URL-safe identifier; lowercase, hyphens only |

**Response (201):**
| Field | Type | Notes |
|---|---|---|
| `tenant_id` | uuid | Assigned by system |
| `name` | string | |
| `slug` | string | |
| `status` | string | Always `"onboarding"` on creation |
| `created_at` | ISO 8601 datetime | |

---

#### POST /v1/onboarding/business-profile
**Roles:** admin, team_lead  
**Sync:** No (triggers async Pipeline 2)  
**Purpose:** Submit the tenant's business profile (Stage 3). Triggers Pipeline 2 in the background. User is not blocked.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `business_type` | enum | Yes | `"B2B"` / `"B2C"` / `"Hybrid"` |
| `industry` | string | Yes | |
| `description` | string | Yes | Free-text business description; minimum 50 chars |
| `target_audience` | string | Yes | Who the tenant sells to |
| `geography_focus` | string[] | Yes | List of country/region strings |
| `product_lines` | string[] | No | |
| `exclusions` | string[] | No | Who to exclude (e.g. "students", "resellers") |

**Response (202):**
| Field | Type | Notes |
|---|---|---|
| `job_id` | uuid | Pipeline 2 run ID |
| `status` | string | `"queued"` |
| `message` | string | `"Scoring intelligence is being built. You can continue to connector setup."` |

---

#### GET /v1/onboarding/status
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** Get the current onboarding readiness state (Stage 5 check). See [[analyses/onboarding-flow-readiness]].

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `tenant_status` | string | `"onboarding"` / `"active"` |
| `pipeline2_complete` | boolean | Pipeline 2 finished successfully |
| `pipeline2_status` | string | `"queued"` / `"running"` / `"completed"` / `"failed"` |
| `active_connectors` | integer | Count of `channel_connection.status = active` |
| `ready_to_activate` | boolean | Both conditions met; can flip to active |
| `failure_reason` | string / null | If `pipeline2_status = "failed"`, the error message |

---

#### GET /v1/tenants
**Roles:** admin  
**Sync:** Yes  
**Purpose:** List all tenants.

**Response (200):** Array of tenant objects.
| Field | Type | Notes |
|---|---|---|
| `tenant_id` | uuid | |
| `name` | string | |
| `slug` | string | |
| `status` | string | `"onboarding"` / `"active"` / `"suspended"` |
| `active_connectors` | integer | |
| `created_at` | ISO 8601 datetime | |

---

#### GET /v1/tenants/{id}/config
**Roles:** admin, team_lead (own tenant)  
**Sync:** Yes  
**Purpose:** Get the tenant's full configuration including scoring weights, bucket thresholds, and operational settings.

**Response (200):** Full `tenant_config` object — see [[analyses/client-config-schema-defaults]] for schema.

Key fields:
| Field | Type | Notes |
|---|---|---|
| `business_type` | string | `"B2B"` / `"B2C"` |
| `scoring_weights` | object | `{fit, intent, engagement, behaviour, context}` — each 0.0–1.0, sum = 1.0 |
| `hot_min` | integer | HOT bucket threshold (default: 80) |
| `warm_min` | integer | WARM bucket threshold (default: 55) |
| `feature_flags` | object | Per-enrichment-provider toggles |
| `concurrency_cap` | integer | Max parallel Scoring Agent calls |
| `token_budget` | integer | Max tokens per LLM call |

---

#### PATCH /v1/tenants/{id}/config
**Roles:** admin, team_lead (limited fields — team_lead cannot change feature_flags or concurrency_cap)  
**Sync:** Yes  
**Purpose:** Update tenant configuration. Takes effect on the next Pipeline 1 run — no in-flight leads are affected.

**Request:** Partial update — send only the fields to change.
| Field | Type | team_lead allowed | Notes |
|---|---|---|---|
| `scoring_weights` | object | Yes | Weights must sum to 1.0 |
| `hot_min` | integer | Yes | |
| `warm_min` | integer | Yes | Must be < `hot_min` |
| `feature_flags` | object | No | admin only |
| `concurrency_cap` | integer | No | admin only |

**Response (200):** Updated `tenant_config` object.

---

#### GET /v1/tenants/{id}/signals
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** List all signal definitions for this tenant (produced by Pipeline 2 Signal Agent).

**Response (200):** Array of signal objects.
| Field | Type | Notes |
|---|---|---|
| `signal_id` | uuid | |
| `dimension` | string | `"fit"` / `"intent"` / `"engagement"` / `"behaviour"` / `"context"` |
| `name` | string | e.g. `"pricing_request"` |
| `description` | string | |
| `weight_within_dim` | float | 0.0–1.0 |
| `applicable_to` | string | `"B2B"` / `"B2C"` / `"both"` |

---

#### PATCH /v1/tenants/{id}/signals
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** Manually adjust signal weights within a dimension. Team lead triggers this after reviewing scoring quality metrics.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `updates` | array | Yes | Array of `{signal_id, weight_within_dim}` |

**Constraint:** Weights within each dimension must sum to 1.0 after update.

**Response (200):** Updated signal array.

**Note:** This does not trigger a Pipeline 2 re-run. Weight changes take effect immediately on the next Pipeline 1 run.

---

## 2. Lead Management

---

#### POST /v1/leads/ingest
**Roles:** admin, team_lead  
**Sync:** No (triggers Pipeline 1)  
**Purpose:** Programmatic lead creation via API (bypasses channel connectors).

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | No | |
| `phone` | string | No | E.164 format: `+91XXXXXXXXXX` |
| `email` | string (email) | No | |
| `source` | enum | Yes | `"email"` / `"whatsapp"` / `"instagram"` / `"sheets"` / `"api"` |
| `raw_message` | string | No | Max 10,000 chars |
| `channel_metadata` | object | No | Platform-specific identifiers |

**Response (202):**
| Field | Type | Notes |
|---|---|---|
| `lead_id` | uuid | |
| `pipeline_stage` | string | `"captured"` |
| `job_id` | uuid | Pipeline 1 run ID |

---

#### POST /v1/leads/upload-csv
**Roles:** admin, team_lead  
**Sync:** No (triggers LLM-assisted column mapping then Pipeline 1)  
**Purpose:** Batch lead ingestion from CSV. Max 50,000 rows, 10 MB.

**Request:** `multipart/form-data`
| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | Yes | `text/csv` only |
| `column_mapping` | JSON object | No | If not provided, LLM-assisted mapping is triggered |

**Response (202):**
| Field | Type | Notes |
|---|---|---|
| `upload_id` | uuid | |
| `row_count` | integer | Rows detected in file |
| `mapping_job_id` | uuid | If mapping is auto-detected |
| `status` | string | `"mapping"` / `"queued"` |

---

#### POST /v1/leads/upload-csv/preview
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** Preview LLM-assisted column mapping before committing. Does not ingest leads.

**Request:** Same as upload-csv.

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `suggested_mapping` | object | `{csv_column: system_field}` |
| `confidence` | object | Per-column mapping confidence |
| `unmatched_columns` | string[] | Columns with no suggested mapping |

---

#### GET /v1/leads
**Roles:** admin, team_lead, salesperson (own assigned leads only)  
**Sync:** Yes  
**Purpose:** List leads with filters.

**Query params:**
| Param | Type | Notes |
|---|---|---|
| `bucket` | string | Filter: `"hot"` / `"warm"` / `"cold"` |
| `pipeline_stage` | string | Filter by stage |
| `assigned_to` | uuid | Filter by salesperson user_id (admin/team_lead only) |
| `needs_review` | boolean | Filter for human review queue |
| `limit` | integer | Default 50, max 200 |
| `cursor` | string | Pagination cursor |

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `leads` | array | Array of lead summary objects |
| `total_count` | integer | |
| `next_cursor` | string / null | |

Lead summary object:
| Field | Type | Notes |
|---|---|---|
| `lead_id` | uuid | |
| `name` | string | PII — not returned to `viewer` role |
| `bucket` | string | |
| `score` | integer | |
| `pipeline_stage` | string | |
| `assigned_to` | uuid / null | |
| `scored_at` | ISO 8601 datetime / null | |
| `sla_deadline` | ISO 8601 datetime / null | |

---

#### GET /v1/leads/{id}
**Roles:** admin, team_lead, salesperson (own assigned only)  
**Sync:** Yes  
**Purpose:** Get full lead detail including score, reasoning, and signal values.

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `lead_id` | uuid | |
| `name` | string | PII |
| `phone` | string | PII (masked: `+91 98****XXXX`) |
| `email` | string | PII (masked) |
| `channel` | string | Source channel |
| `pipeline_stage` | string | |
| `score` | integer / null | |
| `bucket` | string / null | |
| `sub_scores` | object | `{fit, intent, engagement, behaviour, context}` |
| `reasoning` | object | `{primary_driver, signal_contributors, data_gaps, salesperson_note}` |
| `recommended_action` | string | One of 7 enum values |
| `lead_completeness` | float | 0.0–1.0 |
| `needs_review` | boolean | |
| `scored_at` | ISO 8601 datetime / null | |
| `sla_deadline` | ISO 8601 datetime / null | |
| `assigned_to` | uuid / null | |
| `first_contact_date` | ISO 8601 date | |

---

#### GET /v1/leads/{id}/card
**Roles:** admin, team_lead, salesperson (own assigned only)  
**Sync:** Yes  
**Purpose:** Salesperson-optimized view of a lead card. Returns the scored output formatted for the chat interface.

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `lead_id` | uuid | |
| `display_name` | string | Name or "Unknown Lead" |
| `bucket` | string | `"HOT"` / `"WARM"` / `"COLD"` |
| `score` | integer | |
| `salesperson_note` | string | Plain-language explanation from LLM |
| `recommended_action` | string | From enum |
| `sla_deadline` | ISO 8601 datetime / null | |
| `top_signals` | array | Top 3 signal contributors from reasoning |
| `data_gaps` | string[] | What data is missing |
| `needs_review` | boolean | |
| `qualification_prompt` | string / null | For COLD leads with low completeness |

---

#### PATCH /v1/leads/{id}/assign
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** Assign a lead to a salesperson.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `assigned_to` | uuid | Yes | User ID of the salesperson |

**Response (200):** Updated lead summary object.

---

#### POST /v1/leads/{id}/feedback
**Roles:** admin, team_lead, salesperson  
**Sync:** Yes  
**Purpose:** Submit outcome feedback on a lead (thumbs up/down, CRM outcome, notes).

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `outcome_type` | enum | Yes | `"responded"` / `"meeting_booked"` / `"qualified"` / `"deal_closed"` / `"thumbs_up"` / `"thumbs_down"` |
| `notes` | string | No | Max 500 chars |
| `crm_status` | string | No | CRM-side status if available |

**Response (201):** Feedback record confirmation.

---

#### POST /v1/leads/{id}/rescore
**Roles:** admin, team_lead  
**Sync:** No (triggers Pipeline 1)  
**Purpose:** Manually trigger a Pipeline 1 re-score for a specific lead (e.g., after salesperson provides additional data).

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `reason` | string | No | Note on why rescore was triggered |

**Response (202):**
| Field | Type | Notes |
|---|---|---|
| `job_id` | uuid | Pipeline 1 run ID |
| `lead_id` | uuid | |
| `status` | string | `"queued"` |

---

## 3. Pipeline & Orchestration

---

#### POST /v1/pipeline2/run
**Roles:** admin, team_lead  
**Sync:** No (triggers async Pipeline 2)  
**Purpose:** Re-run Pipeline 2 for the current tenant (ICP + Signal Agents). Requires team lead approval — system proposes, team lead triggers. See [[analyses/orchestration-layer-spec]] §3.3.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `scope` | enum | No | `"full"` (all 3 agents) / `"icp_signals"` (Agents 2+3 only) — default `"icp_signals"` |
| `reason` | string | No | Why the re-run is triggered |

**Response (202):**
| Field | Type | Notes |
|---|---|---|
| `job_id` | uuid | Pipeline 2 run ID |
| `status` | string | `"queued"` |

---

#### GET /v1/pipeline/runs/{run_id}
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** Get the status and summary of a pipeline run (Pipeline 1 or Pipeline 2).

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `run_id` | uuid | |
| `pipeline` | string | `"pipeline1"` / `"pipeline2"` |
| `status` | string | `"queued"` / `"running"` / `"completed"` / `"failed"` |
| `started_at` | ISO 8601 datetime / null | |
| `completed_at` | ISO 8601 datetime / null | |
| `leads_processed` | integer | Pipeline 1 only |
| `leads_failed` | integer | Pipeline 1 only |
| `stage_summary` | array | Per-stage status for this run |
| `error` | string / null | On failure |

---

#### GET /v1/pipeline/status/{lead_id}
**Roles:** admin, team_lead, salesperson (own assigned only)  
**Sync:** Yes  
**Purpose:** Get the current pipeline stage for a specific lead.

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `lead_id` | uuid | |
| `pipeline_stage` | string | Current stage value |
| `last_updated` | ISO 8601 datetime | |
| `run_id` | uuid / null | Active run ID if processing |

---

## 4. Webhooks (Inbound)

Webhook endpoints do not use JWT auth. They use HMAC-SHA256 signature validation. See [[analyses/security-planning]] §2.3.

---

#### POST /v1/webhooks/meta/{channel}
**Auth:** HMAC-SHA256 (`X-Hub-Signature-256` header)  
**channel values:** `facebook` / `instagram` / `whatsapp`  
**Purpose:** Receive inbound events from Meta platforms (DMs, Lead Ad form fills, story replies).

**Validation (Step 1 before any processing):**
```
Compute HMAC-SHA256(META_APP_SECRET, raw_request_body)
Compare to X-Hub-Signature-256 header
If mismatch → HTTP 403, log attempt, stop
```

**Request:** Meta webhook payload (JSON). Unknown fields are ignored — Meta adds new fields without notice.

Key fields used:
| Field | Notes |
|---|---|
| `object` | `"page"` / `"instagram"` / `"whatsapp_business_account"` |
| `entry[].messaging[]` | DM events |
| `entry[].changes[]` | Lead Ad events, page events |

**Response (200):** `"EVENT_RECEIVED"` — always return 200 immediately. Processing is async.

**Note:** Meta requires a 200 response within 20 seconds or retries. Do not process inline — enqueue and respond.

---

#### GET /v1/webhooks/meta/verify
**Auth:** None (Meta verification challenge)  
**Purpose:** Webhook URL verification during Meta App setup.

**Query params:** `hub.mode`, `hub.challenge`, `hub.verify_token`

**Response (200):** Returns `hub.challenge` if `hub.verify_token` matches `META_VERIFY_TOKEN`.

---

#### POST /v1/webhooks/email
**Auth:** HMAC or API key (provider-specific)  
**Purpose:** Receive inbound email lead events from email provider webhook.

**Request:** Email webhook payload (provider-specific format). Parsed through Pydantic `EmailWebhookPayload`.

**Response (200):** `"EVENT_RECEIVED"`

---

## 5. Channel Management

---

#### GET /v1/channels
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** List all channel connections for the tenant with their current status.

**Response (200):** Array of `channel_connection` objects.
| Field | Type | Notes |
|---|---|---|
| `channel_id` | uuid | |
| `platform` | string | `"facebook"` / `"instagram"` / `"whatsapp"` / `"email"` |
| `status` | string | `"active"` / `"expired"` / `"pending_verification"` / `"disconnected"` |
| `last_event_at` | ISO 8601 / null | Last successfully ingested event |
| `token_expires_at` | ISO 8601 / null | For Instagram (60-day expiry); null for non-expiring tokens |

---

#### POST /v1/channels/{channel_id}/refresh-token
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Manually trigger an Instagram long-lived token refresh. Use when `token_expires_at` is approaching or if the token was not auto-refreshed by the daily background job. For emergency ops use — the daily job handles routine refresh automatically.

**Path param:** `channel_id` — must be an Instagram channel connection.

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `channel_id` | uuid | |
| `token_expires_at` | ISO 8601 | Updated expiry after refresh (60 days from now) |
| `refreshed_at` | ISO 8601 | |

**Error (400):** If channel is not Instagram type — `"Token refresh only applies to Instagram channels"`  
**Error (404):** Channel not found for this tenant  
**Error (503):** Meta API unavailable — includes retry_after hint

**Note:** Instagram long-lived tokens expire in 60 days. The daily background job refreshes any token with `expires_in < 604800` (7 days). This endpoint provides a manual override for ops without waiting for the background job.

---

#### DELETE /v1/channels/{channel_id}
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Disconnect a channel. Sets `channel_connection.status = 'disconnected'`. Does not delete historical leads captured from that channel.

**Response (204):** No content.

---

## 6. Users & Auth

---

#### POST /v1/users
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Invite a user to a tenant (creates a Clerk invitation).

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string (email) | Yes | |
| `role` | enum | Yes | `"team_lead"` / `"salesperson"` / `"viewer"` |
| `tenant_id` | uuid | Yes | Which tenant this user joins |

**Response (201):**
| Field | Type | Notes |
|---|---|---|
| `user_id` | uuid | |
| `email` | string | |
| `role` | string | |
| `invite_status` | string | `"pending"` |

---

#### GET /v1/users
**Roles:** admin, team_lead (own tenant users only)  
**Sync:** Yes  

**Response (200):** Array of user objects.
| Field | Type | Notes |
|---|---|---|
| `user_id` | uuid | |
| `email` | string | |
| `role` | string | |
| `tenant_id` | uuid | |
| `last_active` | ISO 8601 datetime / null | |

---

#### PATCH /v1/users/{id}/role
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Change a user's role. Role changes always require admin — team leads cannot promote themselves.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `role` | enum | Yes | `"team_lead"` / `"salesperson"` / `"viewer"` |

**Response (200):** Updated user object.

---

## 7. Prompt Management (Admin)

---

#### GET /v1/prompts
**Roles:** admin  
**Sync:** Yes  
**Purpose:** List all prompt templates in the registry.

**Response (200):** Array of prompt objects.
| Field | Type | Notes |
|---|---|---|
| `prompt_id` | uuid | |
| `version` | string | Semver: `v1.3.0` |
| `status` | string | `"draft"` / `"active"` / `"deprecated"` |
| `tenant_id` | uuid / null | null = global |
| `created_at` | ISO 8601 datetime | |
| `activated_at` | ISO 8601 datetime / null | |

---

#### POST /v1/prompts
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Create a new prompt template version. Starts in `draft` status.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `template_body` | string | Yes | The full prompt text with slot placeholders |
| `tenant_id` | uuid | No | If null, applies to all tenants (global) |
| `change_notes` | string | No | What changed from previous version |

**Response (201):** Prompt object with assigned `prompt_id` and `version`.

---

#### PATCH /v1/prompts/{id}/activate
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Promote a draft prompt to `active`. Previous active version is set to `deprecated`. This is an admin-only, audited action.

**Response (200):** Updated prompt object.

**Note:** This action is always logged in `access_log`. An alert is sent to admin confirming the activation.

---

## 8. Delivery & Notifications

---

#### GET /v1/notifications
**Roles:** admin, team_lead, salesperson  
**Sync:** Yes  
**Purpose:** Get the notification feed for the current user. HOT lead push notifications appear here.

**Query params:**
| Param | Type | Notes |
|---|---|---|
| `unread_only` | boolean | Default false |
| `limit` | integer | Default 20 |
| `cursor` | string | |

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `notifications` | array | |
| `unread_count` | integer | |
| `next_cursor` | string / null | |

Notification object:
| Field | Type | Notes |
|---|---|---|
| `notification_id` | uuid | |
| `type` | string | `"hot_lead"` / `"sla_breach"` / `"pipeline2_complete"` / `"pipeline2_failed"` / `"quality_alert"` |
| `title` | string | |
| `body` | string | |
| `lead_id` | uuid / null | For lead-related notifications |
| `read` | boolean | |
| `created_at` | ISO 8601 datetime | |

---

#### PATCH /v1/notifications/{id}/read
**Roles:** admin, team_lead, salesperson  
**Sync:** Yes  

**Response (200):** Updated notification object with `read: true`.

---

#### GET /v1/dashboard
**Roles:** admin, team_lead, viewer  
**Sync:** Yes  
**Purpose:** Get role-scoped dashboard data.

**Response (200):** Role-scoped dashboard object.

For `team_lead`:
| Field | Type | Notes |
|---|---|---|
| `leads_today` | object | `{hot, warm, cold, total}` counts |
| `sla_compliance_hot` | float | % HOT leads actioned within 24h |
| `sla_compliance_warm` | float | % WARM leads actioned within 48h |
| `pipeline_coverage` | float | % leads successfully scored |
| `human_review_queue_size` | integer | |

For `salesperson`:
| Field | Type | Notes |
|---|---|---|
| `my_hot_leads` | integer | Count of assigned HOT leads |
| `my_pending_actions` | integer | Leads requiring action today |
| `my_sla_compliance` | float | My action rate within SLA |

For `viewer`:
| Field | Type | Notes |
|---|---|---|
| `total_leads_this_month` | integer | |
| `bucket_distribution` | object | `{hot_pct, warm_pct, cold_pct}` |
| `hot_response_rate` | float | Aggregated; no PII |

---

## 9. Quality & Reporting

---

#### GET /v1/quality/snapshots
**Roles:** admin, team_lead, viewer (aggregated totals only for viewer)  
**Sync:** Yes  
**Purpose:** Get quality metric snapshots. See [[analyses/scoring-quality-metrics]] for metric definitions.

**Query params:**
| Param | Type | Notes |
|---|---|---|
| `cadence` | enum | `"per_run"` / `"weekly"` / `"monthly"` |
| `from` | ISO 8601 date | Start date |
| `to` | ISO 8601 date | End date |
| `tenant_id` | uuid | admin only; defaults to caller's tenant |

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `snapshots` | array | Array of quality snapshot objects |
| `period` | object | `{from, to}` |

Snapshot object (key fields):
| Field | Type | Notes |
|---|---|---|
| `snapshot_id` | uuid | |
| `cadence` | string | |
| `tenant_id` | uuid | |
| `score_coverage_rate` | float | % leads successfully scored |
| `bucket_distribution` | object | `{hot_pct, warm_pct, cold_pct}` |
| `pipeline_failure_rate` | float | |
| `human_review_rate` | float | |
| `discrimination_ratio` | float / null | Monthly only (AP2) |
| `hot_sla_compliance` | float / null | Weekly only (AR1) |
| `bucket_stability` | float / null | Weekly only (C1) |
| `computed_at` | ISO 8601 datetime | |

---

#### GET /v1/reports/actions
**Roles:** admin, team_lead, salesperson (own metrics only)  
**Sync:** Yes  
**Purpose:** Get action metrics. Salesperson sees own data only.

**Query params:** `from`, `to`, `salesperson_id` (admin/team_lead only)

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `period` | object | `{from, to}` |
| `sla_compliance` | object | Per-bucket SLA compliance rates |
| `action_rate` | object | Per-bucket action rates |
| `mean_time_to_action` | object | Per-bucket median and 90th percentile |
| `action_type_distribution` | object | Per-bucket action type breakdown |

---

## 10. Outbound Webhooks

---

#### POST /v1/tenants/{id}/webhooks
**Roles:** admin, team_lead  
**Sync:** Yes  
**Purpose:** Configure an outbound webhook endpoint to receive scored lead events.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `url` | string (https) | Yes | HTTPS only — HTTP URLs are rejected |
| `events` | string[] | Yes | Event types to subscribe to (e.g. `["lead.scored", "lead.bucket_changed"]`) |
| `description` | string | No | |

**Response (201):**
| Field | Type | Notes |
|---|---|---|
| `webhook_id` | uuid | |
| `url` | string | |
| `secret` | string | HMAC signing secret — shown once; store immediately |
| `events` | string[] | |

---

#### DELETE /v1/tenants/{id}/webhooks/{webhook_id}
**Roles:** admin, team_lead  
**Sync:** Yes  

**Response (204):** No content.

---

## 11. Admin

---

#### GET /v1/admin/feature-flags
**Roles:** admin  
**Sync:** Yes  
**Purpose:** List all feature flags across all tenants.

**Response (200):** Array of `{tenant_id, flag_key, enabled, last_updated}`.

---

#### PATCH /v1/admin/feature-flags
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Toggle a feature flag for a specific tenant.

**Request:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `tenant_id` | uuid | Yes | |
| `flag_key` | string | Yes | e.g. `"enrichment.apollo"` |
| `enabled` | boolean | Yes | |

**Response (200):** Updated flag state.

---

#### GET /v1/admin/audit-log
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Access the append-only audit log. See [[analyses/security-planning]] §3.3.

**Query params:** `from`, `to`, `user_id`, `action_result`, `limit`, `cursor`

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `entries` | array | Array of `access_log` records |
| `next_cursor` | string / null | |

Access log entry:
| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `tenant_id` | string | |
| `user_id` | uuid | |
| `role` | string | |
| `endpoint` | string | e.g. `"GET /leads/{id}"` |
| `resource_id` | string / null | |
| `action_result` | string | `"success"` / `"denied"` / `"error"` |
| `ip_address` | string | |
| `created_at` | ISO 8601 datetime | |

---

#### GET /v1/admin/leads/{id}/lineage
**Roles:** admin  
**Sync:** Yes  
**Purpose:** Inspect the full LLM input/output lineage for a lead. Month 2 feature — at MVP use the CLI script `python manage.py inspect_lineage --lead-id <uuid>`. See [[analyses/security-planning]] confirmed decisions.

**Response (200):**
| Field | Type | Notes |
|---|---|---|
| `lead_id` | uuid | |
| `stages` | array | Per-stage `lineage_record` entries |

Lineage stage entry:
| Field | Type | Notes |
|---|---|---|
| `stage` | string | |
| `agent_id` | string | |
| `input_snapshot` | object | Full decrypted LLM input (PII present) |
| `output_snapshot` | object | Full decrypted LLM output |
| `prompt_version` | string / null | |
| `duration_ms` | integer | |
| `created_at` | ISO 8601 datetime | |

---

## Role Permission Summary

| Endpoint group | admin | team_lead | salesperson | viewer |
|---|---|---|---|---|
| Tenant onboarding | Full | Own tenant | — | — |
| Lead management | Full | Full (own tenant) | Assigned leads | — |
| Lead cards | Full | Full | Assigned leads | — |
| Pipeline triggers | Full | Full | — | — |
| Inbound webhooks | Public (HMAC) | Public (HMAC) | Public (HMAC) | Public (HMAC) |
| Users | Full | Own tenant | — | — |
| Prompt management | Full | — | — | — |
| Notifications | Full | Full | Own | — |
| Dashboard | Full | Full (own tenant) | Own metrics | Aggregate only |
| Quality snapshots | Full | Own tenant | — | Aggregate |
| Action reports | Full | Full | Own | — |
| Outbound webhooks | Full | Own tenant | — | — |
| Admin / feature flags | Full | — | — | — |
| Audit log | Full | — | — | — |
| Lineage inspection | Full | — | — | — |

---

## Caveats & Gaps

- **CRM sync endpoints** — not defined here. CRM sync (Salesforce, HubSpot) is triggered internally by the Delivery Layer after scoring; no external API endpoint is needed at MVP. CRM credentials are configured via `PATCH /v1/tenants/{id}/config`.
- **Real-time lead card delivery** — not an HTTP endpoint. Lead cards are pushed to the salesperson's browser via WebSocket (Pusher/Soketi). The HTTP API is for fetching historical data; real-time delivery is event-driven.
- **Message Parser I/O contract** — the Haiku LLM call for DM parsing does not have a public endpoint. It is internal to the Orchestration Service. See [[analyses/llm-io-contract]] open decisions.
- **Google Sheets / CSV connector setup** — connector configuration endpoint for Google Sheets OAuth is TBD; currently handled as part of the onboarding UI flow.
- **Scheduled reports** — weekly/monthly report delivery is async (email/export). No request-response endpoint at MVP.

## Follow-up Questions

- Should `GET /v1/leads` support full-text search on lead name/company, or filter-only?
- Are there rate limits per endpoint per tenant at MVP, or is rate limiting applied globally?
- Should the salesperson's notification feed be paginated or only return the last 24 hours?
