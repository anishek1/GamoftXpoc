---
type: analysis
question: "Define the Delivery and Integration Layer: APIs, dashboards, notifications, CRM sync, report delivery, and external system outputs."
date: 2026-04-22
tags: [delivery, integration, api, dashboard, notifications, crm-sync, reports, chat-interface, webhooks]
sources_consulted: [sources/2026-lead-intelligence-engine-reference, sources/2026-intelligence-layer-design, sources/2026-core-business-entities]
related: [analyses/orchestration-layer-spec, analyses/governance-observability-layer]
status: COMPLETE — 2026-04-22
---

# Delivery and Integration Layer

**Deliverable:** Subtask — Delivery and Integration Layer definition  
**Audience:** Full product team  
**Date:** 2026-04-22  

---

## 1. What Is the Delivery and Integration Layer?

The Delivery and Integration Layer is everything that happens after a lead gets a bucket. The orchestrator scores the lead, assigns it HOT / WARM / COLD, and then hands it off. The Delivery Layer decides where it goes, who sees it, when they get notified, and how it gets into external systems like a CRM.

This layer is not in the critical path of Pipeline 1. Scoring completes first. Delivery picks up from the Bucketize output and runs from there.

**What it covers:**

| Surface | What it does |
|---|---|
| Chat interface | Ranked lead cards delivered to salespeople in the chat UI — the primary output surface |
| Notifications | Real-time alerts for HOT leads, SLA breaches, system failures, and team lead recommendations |
| Dashboards | Role-scoped views of quality metrics, lead distributions, and SLA compliance |
| CRM sync | Pushing scored leads into external CRM tools the tenant already uses |
| Report delivery | Scheduled summaries (weekly, monthly) delivered to team lead and admin |
| External API and webhooks | Programmatic integration for tenants who want to pull results or receive events |

**Scope — output side only:** This is the *output-side* integration layer. It handles everything that happens to a lead *after* scoring. It is distinct from the [[analyses/channel-integration-layer]], which is the *input-side* integration layer — handling how tenant platforms (WhatsApp, Meta, LinkedIn, website) connect to the system and feed lead events into Pipeline 1. These two layers serve opposite ends of the pipeline and are documented separately.

**Design principle: salespeople never leave the chat interface.**

The chat UI is not one channel among many — it is the primary delivery surface for everything operational. Lead cards arrive in chat. Feedback is submitted in chat. HOT alerts fire in chat. The team lead's feedback recommendations land in chat. The proactive business check-in happens in chat. External dashboards and CRM sync exist for management visibility and integration purposes — they are not the tool salespeople use day to day.

---

## 2. System Position

```
                  PIPELINE 1 ENDS: Bucketize Complete
                                    │
                     scored leads with buckets assigned
                                    │
          ┌─────────────────────────▼────────────────────────────┐
          │             DELIVERY AND INTEGRATION LAYER            │
          │                                                       │
          │   ┌───────────┐  ┌────────────┐  ┌────────────────┐  │
          │   │   CHAT    │  │   NOTIF-   │  │   DASHBOARD    │  │
          │   │ INTERFACE │  │ ICATIONS   │  │   + REPORTS    │  │
          │   │           │  │            │  │                │  │
          │   │ Lead cards│  │ HOT alerts │  │ Quality views  │  │
          │   │ ranked by │  │ SLA breach │  │ per role       │  │
          │   │ bucket    │  │ team lead  │  │ (RBAC-scoped)  │  │
          │   │           │  │ recomm.    │  │                │  │
          │   └───────────┘  └────────────┘  └────────────────┘  │
          │                                                       │
          │   ┌───────────┐  ┌────────────┐  ┌────────────────┐  │
          │   │  CRM SYNC │  │  EXTERNAL  │  │   REPORT       │  │
          │   │           │  │  API +     │  │   DELIVERY     │  │
          │   │ Push leads│  │  WEBHOOKS  │  │                │  │
          │   │ to Salesf.│  │            │  │ Scheduled PDFs │  │
          │   │ HubSpot   │  │ Pull API   │  │ / summaries    │  │
          │   │ etc.      │  │ Push events│  │ to team lead   │  │
          │   └───────────┘  └────────────┘  └────────────────┘  │
          │                                                       │
          │   RBAC enforced across all surfaces                   │
          │   (admin · team_lead · salesperson · viewer)          │
          └───────────────────────────────────────────────────────┘
                    │ feedback signals back
                    ▼
             GOVERNANCE LAYER
          (feedback_events, quality_snapshots, attributed_feedback)
```

**One rule: delivery failures must not roll back Pipeline 1.**

If the chat delivery fails, the score is already written and the lineage is already logged. The lead is not lost. Delivery is retried independently. The orchestrator's job ends when `pipeline_stage = 'delivered'` — what happens after that is the Delivery Layer's responsibility.

---

## 3. Chat Interface — Primary Delivery Surface

### 3.1 Lead Cards

After every Pipeline 1 run, the orchestrator formats the scored leads into lead cards and delivers them in ranked order in the chat interface. HOT leads always appear first.

**Lead card format (one card per lead):**

```
┌───────────────────────────────────────────┐
│ 🔴 HOT  •  Score: 84                      │
│ Priya Mehta — Organic Ventures            │
│ WhatsApp · +91 98765 43210                │
│                                           │
│ "Strong ICP fit and explicit high-intent  │
│  signals — pricing, timeline, and scope   │
│  confirmed via WhatsApp."                 │
│                                           │
│ Action: Call today — high intent          │
│ SLA: Contact within 24 hours              │
│                                           │
│ [👍 Good lead]  [👎 Wrong lead]           │
│ [Mark converted]  [View full profile]     │
└───────────────────────────────────────────┘
```

**What fields come from where:**

| Field | Source |
|---|---|
| Bucket (HOT/WARM/COLD) | Bucketize stage — set by orchestrator |
| Score (0–100) | ScoringOutput.score — from Scoring Agent |
| Reasoning text | ScoringOutput.reasoning — one-line string from Scoring Agent |
| Recommended action | ScoringOutput.recommended_action — from Scoring Agent |
| SLA reminder | Set by orchestrator based on bucket: HOT=24h, WARM=2-3d, COLD=weekly |
| Feedback buttons | UI controls — write to `feedback_events` via API |

**What the salesperson does NOT see:**

- Raw signal values (e.g., `pricing_request: true`) — these are internal scoring inputs, not customer-facing
- sub_scores / dimension breakdown — too technical; available to team lead on request in full profile view
- lead_completeness value — also internal; visible in admin/team lead views only

**HOT leads get a push notification immediately.** WARM and COLD leads are delivered in the ranked list but do not trigger a push.

### 3.2 Delivery Timing

| Trigger | Delivery timing |
|---|---|
| Salesperson interactive run ("who should I call today?") | Delivered immediately after run completes |
| Scheduled run | Delivered when run completes — salesperson sees updated list when they next open chat |
| Webhook-triggered run (new lead just arrived) | `[TBD — immediate delivery vs batch with next run]` |

### 3.3 What Else Gets Delivered in Chat

The chat interface is not just for lead cards. Everything that needs human attention routes through the same interface:

| Event | Who receives it | What it looks like |
|---|---|---|
| HOT lead push alert | Assigned salesperson | Immediate push: "New HOT lead — Priya Mehta. Contact within 24 hours." |
| SLA breach alert | Assigned salesperson + team lead | "HOT lead [name] has not been contacted in 24 hours." |
| Team lead enforcement recommendation | Team lead | Structured message: pattern + evidence + 5 action options (see governance doc Section 5.5) |
| Pipeline failure alert | Admin + team lead | "Run [run_id] failed — [reason]. X leads could not be processed." |
| Proactive business check-in | Team lead | "Has anything changed in your business recently?" (scheduled; see governance doc Section 5.7) |
| Pipeline 2 re-run proposal | Team lead | "A significant change was detected. Should I update your scoring profile?" |

All of these use the **same chat surface, same thread**. No new notification channels are introduced unless the team decides to add email (see Section 4).

### 3.4 Human Review Queue in Chat

Leads routed to human review (`pipeline_stage = 'human_review'`) appear in a separate section in the chat interface — not in the main ranked lead list. This is a filtered view of the `leads` table where `pipeline_stage = 'human_review'`.

Two reasons a lead lands here:
1. `needs_review = true` from the Scoring Agent (lead_completeness below threshold)
2. Scoring Agent failed after retries (`reason: scoring_failed`)

The review card shows which reason applied, so the salesperson (or team lead) knows whether the issue is missing data or a scoring system error.

---

### 3.5 Awaiting Clarification in Chat

Leads in `pipeline_stage = 'awaiting_clarification'` appear in a distinct holding section in the chat interface — separate from the main ranked lead list and separate from the human review queue.

**What this means:** The Intent Gate fired (very low intent + high fit) and the system sent a clarification prompt to the lead via their originating channel (WhatsApp → WhatsApp, Instagram DM → Instagram DM). The lead is paused. No score has been assigned yet.

**Salesperson restriction — CRITICAL:** A salesperson **cannot** manually send a message to a lead in `awaiting_clarification` state. The chat interface blocks outbound messaging for these leads. This is intentional: the lead has already received a system-generated clarification request. If the salesperson also reaches out independently, the lead receives two simultaneous messages from "the business" with different framings, which is confusing and damages trust. The restriction lifts automatically when the lead replies (resuming to scored state) or when the 24-hour timeout expires and the lead is scored with an intent penalty.

The chat card for an `awaiting_clarification` lead shows:
- Lead name, channel, timestamp of original message
- The clarification question that was sent
- Time remaining until 24h timeout
- Status: "Waiting for reply" (no score card, no bucket)

---

## 4. Notifications

### 4.1 What Triggers a Notification

| Event | Who gets it | Priority | Channel |
|---|---|---|---|
| HOT lead delivered | Assigned salesperson | High | Chat (push) |
| SLA breach — HOT uncontacted after 24h | Salesperson + team lead | High | Chat `[+email TBD]` |
| SLA breach — WARM uncontacted after 3d | Salesperson | Medium | Chat |
| Human review queue > 20% of run | Team lead | Medium | Chat |
| Pipeline failure rate > 5% | Admin + team lead | High | Chat |
| All sources fail in a run | Admin + team lead | Critical | Chat + email |
| Pattern detection threshold crossed | Team lead | Medium | Chat |
| Pipeline 2 failure (any onboarding agent) | Admin | High | Chat + email |
| Feedback rate drops below 20% | Team lead | Medium | Chat |

### 4.2 How Notifications Are Delivered

The `notification_delivery` entity in S1 records every notification sent — to whom, what triggered it, when, and what channel was used. This makes notifications auditable and prevents duplicate alerts.

**Delivery channels:**

| Channel | When used | Status |
|---|---|---|
| Chat (in-app) | All routine notifications — lead cards, SLA alerts, recommendations | Default |
| Email | Critical failures (all sources down, Pipeline 2 failure) + `[TBD — team decision whether email is added for SLA breaches]` | TBD for non-critical |
| Both | `[TBD — team decision on channel hierarchy]` | TBD |

**Push vs in-thread:**

- HOT lead alert = push notification (surfaces even if chat is not open)
- Everything else = in-thread message (visible when salesperson opens chat)

**Notification deduplication:**

The same alert type fires once per event per recipient. If a HOT lead SLA breach has already been sent to the salesperson, it does not re-fire every hour. A follow-up escalation (e.g., to team lead) fires separately after an additional threshold is crossed.

Deduplication logic: `[TBD — track by notification_delivery.lead_id + event_type + sent_at]`

### 4.3 The `notification_delivery` Entity

S1's entity catalog confirms `notification_delivery` as a formal entity. It records:

| Field | What it captures |
|---|---|
| `id` | Unique notification record |
| `tenant_id` | Which tenant |
| `recipient_id` | Who received it (user_id) |
| `recipient_role` | salesperson / team_lead / admin |
| `notification_type` | hot_lead_alert / sla_breach / pattern_flagged / pipeline_failure / etc. |
| `lead_id` | Which lead triggered it (null for system-level notifications) |
| `channel` | chat / email / both |
| `payload` | The message content |
| `sent_at` | When it was sent |
| `acknowledged_at` | When the recipient acknowledged or dismissed it |

This entity is also queried by the AR1 (SLA Compliance) metric — the quality job checks `notification_delivery` records to verify that HOT lead alerts were sent, and then cross-references with salesperson action timestamps to measure whether they were acted on within the SLA window.

---

## 5. Dashboards

### 5.1 What Dashboards Are For

Dashboards are not for salespeople — they are for team leads, admins, and viewers who need aggregated visibility without wading through individual lead cards in chat. The salesperson's view is the chat interface; the team lead's view is a combination of chat (for time-sensitive items) and dashboard (for trend review).

S1 confirms `dashboard_definition` as a formal entity — each tenant can have multiple dashboard configurations, each defined by which metrics and views it shows, for which role.

### 5.2 What Each Role Sees

**Admin:**
- Cross-tenant pipeline health overview
- Per-tenant run history, success rates, failure rates
- All quality snapshots across all tenants
- Credential and config status per tenant
- User management

**Team Lead** (scoped to own tenant — RLS enforced):
- Current run summary: leads scored, buckets, human review count
- Lead completeness distribution (how well-enriched leads are)
- Quality metric dashboard — all three cadences (per-run, weekly, monthly) for their tenant
- SLA compliance rates (AR1) — are salespeople contacting HOT leads within 24h?
- Feedback rate — what % of delivered leads have been rated?
- Bucket distribution over time — is the HOT/WARM/COLD split stable?
- Pattern detection results (what the weekly job flagged)
- Active enforcement recommendations

**Salesperson** (scoped to own assigned leads — additional RBAC filter):
- Their personal lead list (not a dashboard — this is the chat interface)
- Their own AR3/AR4 metrics: their time-to-action distribution and action types taken
- No access to other salespeople's lead data

**Viewer** (aggregated only — no lead PII):
- Aggregated quality snapshots: overall score coverage, bucket distribution rates
- No individual lead cards, no PII, no salesperson-level breakdowns

### 5.3 Dashboard Tooling

The `dashboard_definition` entity stores the definition of each dashboard (which metrics, which view, which role) — not the dashboard UI itself. The actual rendering can be:

- **In-product dashboard** — built into the chat product as a separate tab or view for team leads
- **External BI tool** — Grafana, Metabase, or similar reading from `quality_snapshots` via a read-only connection
- **Both** — internal for team leads, external BI for the admin / product owner

Dashboard tooling: `[TBD — team decision. Recommend starting with an in-product view using quality_snapshots as the data source, since that table already exists and is scoped by tenant_id + metric_id]`

### 5.4 The `dashboard_definition` Entity

| Field | What it captures |
|---|---|
| `id` | Unique dashboard record |
| `tenant_id` | Which tenant this dashboard is for |
| `dashboard_name` | Human-readable name (e.g., "Team Lead Weekly View") |
| `role` | Which RBAC role can see this dashboard |
| `metric_ids` | List of quality metric IDs to include |
| `refresh_cadence` | How often the data refreshes (per-run / daily / weekly) |
| `created_at` | When the dashboard was created |

---

## 6. CRM Sync

### 6.1 What Gets Synced and When

When a lead is delivered (pipeline_stage = 'delivered'), the Delivery Layer can push the scored result to the tenant's external CRM — Salesforce, HubSpot, Zoho, or any CRM that supports a REST API.

**What goes into the CRM:**

| Field | Source | Why push it |
|---|---|---|
| Lead identity (name, phone, email) | `leads` table | CRM needs to identify the contact |
| Bucket (HOT/WARM/COLD) | Scoring output | This is the primary decision signal for sales follow-up |
| Score (0–100) | ScoringOutput.score | Helps salespeople prioritise within a bucket |
| Recommended action | ScoringOutput.recommended_action | One-line instruction — actionable in CRM context |
| Reasoning | ScoringOutput.reasoning | Brief explanation for why the lead has this score |
| SLA deadline | Computed by orchestrator from bucket | Enables CRM task auto-creation with due date |
| Last synced timestamp | System-generated | Prevents stale overwrites |

**What does NOT get synced:**

- sub_scores (dimension breakdown) — too granular for most CRM fields; stored internally in `lead_score` for quality metrics use
- signal values — internal enrichment data, not for CRM
- lead_completeness — internal metric; not meaningful to an external CRM user

### 6.2 Sync Timing

| Bucket | Sync timing | Why |
|---|---|---|
| HOT | Immediate push on delivery | HOT leads need to appear in the CRM before the 24h SLA clock starts |
| WARM | Immediate push on delivery | Still time-sensitive within 2–3 day window |
| COLD | `[TBD — immediate vs. batched daily]` | Lower urgency; batching may be more efficient depending on volume |
| human_review | Not pushed until resolved | Pushing unreviewed leads to CRM creates noise — wait for human to confirm bucket |
| awaiting_clarification | Not pushed | Lead is paused awaiting clarification reply; pipeline has not completed; no score to push |
| failed | Not pushed | Failed leads have no reliable score to push |

### 6.3 Sync Direction

**Primary: one-way outbound.** The Lead Intelligence Engine pushes enriched, scored leads to the CRM. The CRM is a consumer of output.

**Optional: inbound outcome data.** If the CRM tracks whether a lead converted (deal closed, deal lost), that outcome data is valuable for the AP1 (Bucket Outcome Rate) quality metric. Pulling outcome data back from the CRM would replace or supplement salesperson thumbs-up/down feedback.

Bidirectional sync: `[TBD — team decision. Requires mapping CRM deal stages to the system's 'converted / not_converted' outcome field. Recommended for Month 2+ after feedback loop is running from chat]`

### 6.4 The `delivery_endpoint` Entity

S1's entity catalog confirms `delivery_endpoint` as a formal entity. It stores the configuration for every external destination — whether that is a CRM, a webhook endpoint, or any other integration point.

| Field | What it captures |
|---|---|
| `id` | Unique endpoint record |
| `tenant_id` | Which tenant this endpoint belongs to |
| `endpoint_type` | crm / webhook / email / api_push |
| `endpoint_name` | Human-readable label (e.g., "Urvee Salesforce Org") |
| `url` | The target URL |
| `credentials_ref` | Reference to the secrets vault path — never the credential itself |
| `active` | Whether this endpoint is currently receiving pushes |
| `last_synced_at` | Timestamp of last successful push |
| `error_count` | Consecutive failures since last success |

**One delivery_endpoint record per integration per tenant.** A tenant connected to both Salesforce and a custom webhook has two `delivery_endpoint` records — both scoped to their tenant_id, isolated by RLS.

### 6.5 CRM Failure Handling

CRM endpoints are external systems and can fail independently of the Lead Intelligence Engine.

| Failure mode | What happens |
|---|---|
| CRM returns 5xx | Retry with exponential backoff: 1 min, 5 min, 30 min |
| CRM returns 4xx (auth failure) | Do not retry — alert admin (credential may need rotation) |
| Timeout | Retry once — if timeout again, log and alert admin |
| 3 consecutive failures | Mark `delivery_endpoint.active = false`, alert admin, stop pushing until reconnected |

Lead data is not lost when a CRM push fails — it is still in the `leads` table and `lead_score` entity. The retry resolves the sync gap. The `notification_delivery` entity records the failure event.

---

## 7. External API and Webhook Layer

### 7.1 Why an External API Exists

Not all tenants want their leads delivered only via chat. Some have custom dashboards, existing operational tools, or downstream systems that need to receive lead data programmatically. The external API layer makes the Lead Intelligence Engine's output available to those systems without requiring them to integrate with the chat interface.

**Two modes:**

| Mode | Direction | How it works |
|---|---|---|
| Push (webhook) | Outbound — engine pushes to external system | On delivery, the engine POSTs the scored lead payload to the tenant's registered webhook URL |
| Pull (REST API) | Inbound — external system queries the engine | External system makes authenticated GET requests for leads, scores, and quality snapshots |

### 7.2 What the API Exposes

**Lead endpoints (REST):**

```
GET /api/v1/leads
  → Returns scored leads for the tenant (paginated, filterable by bucket, pipeline_stage, date)
  → Auth: JWT required (tenant_id scoped — RLS applies)
  → Role required: team_lead or admin

GET /api/v1/leads/{lead_id}
  → Full lead profile including score, sub_scores, reasoning, pipeline_stage
  → Auth: JWT required
  → Role required: salesperson (own assigned leads only), team_lead, admin

GET /api/v1/leads/{lead_id}/lineage
  → Full lineage chain for a lead (pipeline stages, input/output per stage, prompt versions)
  → Auth: JWT required
  → Role required: admin or team_lead
```

**Quality endpoints (REST):**

```
GET /api/v1/quality/snapshots
  → Returns quality_snapshots for the tenant, filterable by metric_id and cadence
  → Auth: JWT required
  → Role required: team_lead or admin

GET /api/v1/quality/snapshots/{metric_id}
  → Returns time series for a specific quality metric
```

**Webhook (push):**

When a tenant registers a webhook URL in their `delivery_endpoint` record, the engine POSTs a JSON payload to that URL each time a lead batch is delivered. The receiving system is responsible for processing the payload.

**Webhook payload format:**

```json
{
  "event": "leads.delivered",
  "tenant_id": "gamoft_001",
  "run_id": "uuid",
  "delivered_at": "2026-04-22T14:32:00Z",
  "leads": [
    {
      "lead_id": "uuid",
      "name": "Priya Mehta",
      "phone": "+91 98765 43210",
      "bucket": "hot",
      "score": 84,
      "reasoning": "Strong ICP fit and explicit high-intent signals.",
      "recommended_action": "Call today — high intent, strong fit",
      "sla_deadline": "2026-04-23T14:32:00Z",
      "needs_review": false
    }
  ]
}
```

**Note:** PII fields (name, phone, email) are included in the webhook payload. Webhook endpoints must be HTTPS. Tenant is responsible for securing their receiving endpoint. The engine does not push to HTTP endpoints.

### 7.3 Authentication

The external API uses the same JWT authentication defined in the governance layer (Section 7.3 of governance doc):

- Every API request must carry a valid JWT token
- Token carries `tenant_id` and `role` claims
- Server validates signature → sets Postgres session variable → RLS activates automatically
- Tokens expire after 1 hour; refresh tokens rotate on use

Webhook delivery uses a **webhook signature** in addition to HTTPS:

```
X-Gamoft-Signature: sha256=<hmac-sha256 of request body using tenant-specific secret>
```

The receiving endpoint verifies the signature before processing the payload. The tenant's webhook secret is stored in the secrets vault — same vault path mechanism as channel credentials.

### 7.4 API Versioning and Rate Limits

**Versioning:** `/api/v1/` prefix. Breaking changes require a new version (`/api/v2/`). The current schema is `v1`. Tenants using the API are notified before a major version change.

**Rate limits:** `[TBD — team decision. Suggest per-tenant limit: 100 requests/minute for REST, no rate limit on webhooks since they are push from our side]`

**API documentation format:** `[TBD — OpenAPI / Swagger spec to be generated when API is implemented]`

---

## 8. Report Delivery

### 8.1 What Reports Are

Reports are scheduled summaries of quality metrics, delivered directly to the team lead or admin — they do not need to open a dashboard to get a weekly or monthly digest. The `report_definition` entity in S1 defines what each report contains, how often it runs, who gets it, and in what format.

### 8.2 Report Types

**Weekly report — for team lead:**

Delivered every Monday morning, covering the past 7 days.

| Section | Metric | Source |
|---|---|---|
| Run summary | Total runs, leads scored, score coverage rate | `quality_snapshots` per-run metrics |
| SLA compliance | AR1 — % HOT leads contacted within 24h | `quality_snapshots` weekly |
| Action rate | AR2 — % leads with any action taken per bucket | `quality_snapshots` weekly |
| Score stability | C1 — % leads in same bucket across consecutive runs | `quality_snapshots` weekly |
| Human review volume | Count of leads in human_review queue | `leads` table |
| Feedback rate | % delivered leads with thumbs up/down submitted | `feedback_events` |

**Monthly report — for team lead + product owner:**

Covers the past 30 days. Requires outcome data to be meaningful.

| Section | Metric | Source |
|---|---|---|
| Bucket outcome rates | AP1 — HOT/WARM/COLD conversion rates | `quality_snapshots` monthly |
| Bucket separation | AP2 — discrimination ratio (HOT BOR / COLD BOR) | `quality_snapshots` monthly |
| Score decay summary | Leads decayed, auto-moved to COLD | `leads` table + decay job logs |
| Weight adjustment recommendation | If AP1 HOT rate is low, include a weight review note | Generated by quality job |
| Salesperson priority alignment | AR5 — are salespeople choosing HOT leads? | `quality_snapshots` monthly |
| Global KPI summary | System Health + Business Health + Tenant Health Rate | `quality_snapshots` |

### 8.3 Delivery Channel for Reports

Reports are delivered via:

- **Chat** — as a structured message thread to the team lead, with a summary and link to full report
- **Email** — full formatted report attached or linked

Report format: `[TBD — PDF / inline chat / structured HTML email]`

Report delivery channel: `[TBD — team decision]`

### 8.4 The `report_definition` Entity

| Field | What it captures |
|---|---|
| `id` | Unique report record |
| `tenant_id` | Which tenant |
| `report_name` | Human-readable label (e.g., "Weekly Team Lead Summary") |
| `cadence` | weekly / monthly |
| `recipient_role` | team_lead / admin / both |
| `metric_ids` | Which metrics to include |
| `delivery_channel` | chat / email / both |
| `format` | `[TBD — pdf / html / markdown]` |
| `next_delivery_at` | Scheduled next run time |

---

## 9. What Each Role Sees — Unified View

This table pulls together the RBAC-scoped access across all delivery surfaces.

| Surface | Admin | Team Lead | Salesperson | Viewer |
|---|---|---|---|---|
| Chat — lead cards | All tenants | Own tenant leads | Own assigned leads | No access |
| Chat — HOT alerts | Own assigned leads | Own tenant HOT alerts | Own assigned HOT leads | No access |
| Chat — SLA breach alerts | All breach alerts | Own tenant salesperson breaches | Own assigned breaches | No access |
| Chat — team lead recommendations | All | Own tenant only | No | No |
| Chat — pipeline failure alerts | All | Own tenant | No | No |
| Dashboard | Cross-tenant health | Own tenant quality metrics + SLA | Personal action metrics only | Aggregated KPIs only (no PII) |
| Quality snapshots (API) | All tenants | Own tenant | No | No |
| Lead profile + lineage (API) | All | Own tenant | Own assigned leads | No |
| CRM sync | Configure for any tenant | View sync status | No | No |
| Reports | All | Own tenant weekly + monthly | No | No |
| Webhook registration | Configure for any tenant | No | No | No |

RLS enforces tenant scoping at the database level. Role checks at the API endpoint level enforce what within a tenant each role can see. Both layers must pass independently.

---

## 10. Data Entities

The four S1 delivery entities, and what they cover:

| Entity | What it stores | Who writes to it | Who reads it |
|---|---|---|---|
| `dashboard_definition` | Dashboard config per role per tenant | Admin (setup) | Dashboard rendering layer |
| `notification_delivery` | Record of every notification sent | Delivery layer | Quality jobs (AR1 uses this), admin audit |
| `delivery_endpoint` | External integration config (CRM, webhook URLs) | Admin (setup) | Delivery layer on every push |
| `report_definition` | Report config per cadence per tenant | Admin (setup) | Report job runner |

These entities live in S1's Operational Observability & Delivery group. They do not contain lead data — they contain **configuration and delivery records**. The lead data they reference by ID comes from the `leads` and `lead_score` entities.

---

## 11. How Delivery Connects to Other Layers

**Delivery and Governance are not the same layer, but they are tightly coupled.**

- The feedback buttons on every lead card (thumbs up/down) write to `feedback_events` — which the Governance Layer's feedback loop reads
- `notification_delivery` records are read by the AR1 quality metric job to verify SLA alerts were sent
- Team lead recommendations (Step 3 of the feedback loop) are delivered via the same chat surface as lead cards
- Dashboard data is read from `quality_snapshots` — which are written by Governance Layer quality jobs

**Delivery and Orchestration have a clean handoff.**

The orchestrator's job ends when:
1. `lead_score` and `pipeline_run` are written
2. `pipeline_stage = 'delivered'` is set on the lead

After that, the Delivery Layer takes over. It reads the `lead_score` and `leads` entities and handles formatting, routing, CRM push, and notification — the orchestrator does not participate.

**One exception: HOT lead notification.**

The orchestrator sets a flag on the run output indicating which leads are HOT. The Delivery Layer reads this flag and fires the push notification immediately. The timing dependency is: Bucketize finishes → HOT flag read → push notification sent → lead card delivered in ranked list. This all happens within the same pipeline run completion event.

---

## 12. Open Decisions

| Decision | Owner | Status |
|---|---|---|
| Alert delivery channel for SLA breaches (chat / email / both) | Team | `[TBD]` |
| Alert delivery channel for pattern detection recommendations | Team | `[TBD]` |
| Report format (PDF / HTML / inline chat message) | Team | `[TBD]` |
| Dashboard tooling (in-product vs Grafana/Metabase vs both) | Team | `[TBD — recommend starting with in-product using quality_snapshots]` |
| CRM sync timing for COLD leads (immediate vs daily batch) | Team | `[TBD]` |
| Bidirectional CRM sync for outcome data (inbound) | Team | `[TBD — recommended for Month 2+ after chat feedback loop is running]` |
| Webhook rate limiting rules | Team | `[TBD]` |
| REST API rate limits per tenant | Team | `[TBD — suggest 100 req/min]` |
| Notification deduplication window | Team | `[TBD]` |
| Webhook-triggered run delivery: immediate vs batched with next run | Team | `[TBD]` |
| Report delivery for COLD bucket: weekly summary or omit | Team | `[TBD]` |
| Viewer role dashboard scope — which aggregate KPIs are shown | Team | `[TBD]` |

---

## 13. Confirmed Decisions

| Decision | Basis |
|---|---|
| Primary delivery surface is the chat interface | Source doc Section 11.6 — "salespeople never leave the chat interface" |
| Lead cards delivered ranked by bucket (HOT first) | Source doc + team decision |
| HOT leads get immediate push notification; WARM/COLD get list delivery only | Source doc + team decision |
| Feedback buttons embedded in every lead card (thumbs up/down + outcome) | Source doc Section 11.6 |
| Human review leads surfaced as separate section in chat — no separate table | S1 entity catalog 2026-04-22 (filtered view of leads table) |
| All team lead alerts (recommendations, check-ins, failures) go through chat | Team decision |
| RBAC-scoped access across all delivery surfaces | Governance layer decision 2026-04-19 |
| RLS enforces tenant isolation at DB level — delivery layer inherits this | Governance layer decision 2026-04-19 |
| Four S1 delivery entities: dashboard_definition, notification_delivery, delivery_endpoint, report_definition | S1 entity catalog 2026-04-22 |
| HOT leads pushed to CRM immediately on delivery | Team decision |
| CRM and webhook credentials stored in secrets vault — never in DB | Governance layer credential management (LOCKED) |
| Webhook endpoints must use HTTPS; payloads signed with HMAC-SHA256 | Security requirement |
| Delivery failures do not roll back Pipeline 1 — scoring result is persisted independently | Team decision |
| notification_delivery is a formal entity (auditable, used by quality metrics) | S1 entity catalog 2026-04-22 |
| Report cadences: weekly (for team lead) + monthly (for team lead + product owner) | Governance layer quality tracking decisions 2026-04-19 |
| Three quality cadences drive report content — per-run, weekly, monthly snapshots | Governance layer decision 2026-04-19 |
| Lead PII encrypted at rest; delivery layer decrypts at application layer only | Governance layer security decision 2026-04-19 |
