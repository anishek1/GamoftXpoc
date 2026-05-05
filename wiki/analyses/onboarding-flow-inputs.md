---
type: analysis
question: "What are the required inputs for each onboarding stage — field names, types, validation rules, sources (user vs system), and which fields are explicitly not collected from the user?"
date: 2026-05-05
tags: [onboarding, pipeline-2, tenant-setup, connector-setup, inputs, validation, form-fields]
sources_consulted:
  - "[[concepts/lead-pipeline-architecture]]"
  - "[[concepts/persona-layer]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/channel-integration-layer]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/execution-type-classification]]"
  - "[[analyses/meta-integration-implementation]]"
  - "[[sources/2026-core-business-entities]]"
status: COMPLETE — Subtask 2 of 3 (inputs only; stage map in onboarding-flow-stage-map, completion criteria in onboarding-flow-readiness)
---

# Onboarding Flow — Required Inputs

**Question:** What are the required inputs for each onboarding stage — field names, types, validation rules, sources (user vs system), and which fields are explicitly not collected from the user?
**Date:** 2026-05-05

---

## Answer / Finding

Six fields are collected from the user across four onboarding stages. Stage 5 collects nothing — it is a system readiness check. Approximately a dozen PersonaObject fields are commonly mistaken as form inputs but are LLM-inferred. These are explicitly catalogued below to prevent developer confusion.

---

## Stage 1 — Account Creation Inputs

| Field | Source | Type | Required | Validation |
|-------|--------|------|----------|------------|
| `email` | User | string | Yes | RFC 5322 format; must be unique across all accounts |
| `password` | User | string | Required unless SSO | Min 8 characters; at least 1 uppercase, 1 number, 1 special character; not stored in plaintext |
| `full_name` | User | string | Yes | Min 2 characters, max 100 characters; no leading/trailing whitespace |
| `tos_accepted` | User | boolean | Yes | Must be `true`; user must explicitly check the box — pre-checked is not acceptable |
| `email_verified` | System | boolean gate | Yes (auto) | System-generated; set to `true` when user clicks verification link; Stage 2 does not unlock until `true` |

**SSO path:** If user authenticates via SSO (Google, Microsoft, etc.), `email` and `full_name` are pre-populated from the identity provider. `password` is not collected. `tos_accepted` still requires explicit user action.

**System-generated (not user input):**
- `user_id` — UUID generated on form submit
- `created_at` — server timestamp on record creation

**Validation notes:**
- Email uniqueness checked on submit (not on blur) to avoid enumeration attacks — return a generic "account already exists or email is invalid" message on duplicate
- Password is never echoed back or logged; evaluated server-side against complexity rules only
- `tos_accepted = false` on submit → form blocked; error shown inline on the checkbox

---

## Stage 2 — Organization Setup Inputs

| Field | Source | Type | Required | Validation |
|-------|--------|------|----------|------------|
| `organization_name` | User | string | Yes | 2–100 characters |
| `organization_slug` | User | string | Yes | Auto-generated from `organization_name` (lowercase, hyphens replace spaces, non-alphanumeric stripped); user can edit; must be globally unique; lowercase alphanumeric + hyphens only; 3–50 characters |

**System-generated (not user input):**
- `tenant_id` — UUID generated on org record creation
- `tenant.status` — set to `onboarding` at creation; not user-editable
- Admin role assignment — the creating user is automatically assigned `tenant_admin` role; no user input required

**Validation notes:**
- Duplicate `organization_slug` → prompt to choose another; do not expose which org holds the slug (enumeration risk)
- Slug auto-generation preview shown live as the user types `organization_name`; user can override before submit
- On system error during record creation: no partial state committed; retry option shown; `tenant.status` is not set until the record fully commits

---

## Stage 3 — Business Profile Inputs

This is the most complex input stage. The form collects six fields from the user. All other PersonaObject fields are LLM-inferred by the Persona Agent — they are never collected from the user.

### Fields Collected from User

| Field | Source | Type | Required | Validation |
|-------|--------|------|----------|------------|
| `business_type` | User | enum | Yes | One of: `B2B`, `B2C`, `Hybrid`; collected first because it controls the adaptive label on `target_audience` |
| `industry` | User | string | Yes | 3–100 characters; free text (no controlled vocabulary at MVP) |
| `business_description` | User | string | Yes | 150–2000 characters; must describe what the business does, who it serves, and what it sells |
| `target_audience` | User | string (multi-entry) | Yes | At least 1 entry required; label adapts per `business_type` (see below); each entry max 200 characters |
| `geography_focus` | User | string (multi-entry) | Yes | At least 1 entry required; free text at MVP (country, city, or region); each entry max 100 characters |
| `negative_profiles` | User | string (multi-entry) | Optional | Can be empty; describes lead types to exclude (e.g., "students", "job seekers"); each entry max 200 characters |

**`target_audience` label adaptation:**
- `business_type = B2B` → label: *"Who are your ideal customers? (describe the companies and roles you sell to)"*
- `business_type = B2C` → label: *"Who are your ideal customers? (describe the type of person you sell to)"*
- `business_type = Hybrid` → label: *"Who are your ideal customers? (describe both the businesses and individuals you sell to)"*; validation: at least one B2B entry AND at least one B2C entry must be present

**`business_description` minimum guidance shown to user:**
The form displays helper text: *"Describe what your business does, who you serve, and what you sell or offer. A stronger description produces better lead scoring."* Minimum 150 characters is enforced; the UI shows a live character count.

### LLM-Strengthening Step (P2-1 HYBRID)

After the user submits the Stage 3 form, the system performs a single LLM call to strengthen the `business_description` before passing inputs to the Persona Agent. This is the P2-1 HYBRID step in [[analyses/execution-type-classification]].

Flow:
1. User submits the 6-field form
2. System calls LLM with the raw `business_description` + `business_type` + `industry`
3. LLM returns a strengthened description (expands vague phrases, fills obvious gaps, preserves user intent)
4. System shows the user a confirmation screen: *"Here is how we interpreted your business description — does this look right?"*
   - User approves → Persona Agent queued with the strengthened description
   - User edits → edits captured; Persona Agent queued with the edited version
5. Stage 4 unlocks; Pipeline 2 begins in the background

This step is transparent to the user. The original user-submitted description is preserved in storage alongside the strengthened version.

### Fields Explicitly NOT Collected from User (LLM-Inferred)

These fields appear in the PersonaObject and IcpDefinition but are produced by the Persona Agent, not collected from the user during onboarding.

| Field | Inferred By | Where It Appears |
|-------|-------------|-----------------|
| `sales_cycle` | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `ticket_size` | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `decision_complexity` | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `company_size_preference` | Step 2 ICP Agent (LLM) | IcpDefinition |
| `scoring_weights` | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `banding` (hot_min, warm_min, cold_max) | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `icp_description` | Step 2 ICP Agent (LLM) | IcpDefinition |
| `signal[]` (all 5 dimensions) | Step 3 Signal Agent (LLM) | signal entity |
| `custom_rules` | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `tone` | Step 1 Onboarding Agent (LLM) | PersonaObject |
| `priority_signals` | Step 2 ICP Agent (LLM) | IcpDefinition → PersonaObject |

**Rule:** No onboarding form field should map to any LLM-inferred field. If a future developer proposes collecting these from the user as form inputs, redirect them to the Persona Agent's inference role.

---

## Stage 4 — Connector Setup Inputs

Stage 4 is primarily OAuth flows, not form fields. User inputs are minimal; the heavy lifting is the OAuth redirect sequence and post-OAuth system configuration.

### Facebook (Meta) Connector

| Step | Field / Action | Source | Type | Required |
|------|---------------|--------|------|----------|
| 1 | Initiate OAuth | User action | Click | Yes |
| 2 | Facebook OAuth redirect | Facebook | OAuth 2.0 | Yes |
| 3 | `page_selection` | User | select (if >1 page exists) | Conditional: required if user has more than 1 Facebook Page; auto-selected if user has exactly 1 Page |
| 4 | `channel_connection` record | System | auto-created | — |

**Post-OAuth system actions (not user inputs):**
- Short-lived token → long-lived token exchange (server-side)
- Long-lived token → non-expiring Page Access Token exchange (server-side)
- PSID follow-up call on lead DM events (runtime, not onboarding)
- Webhook subscription registered per selected Page
- `channel_connection.status = active` set on successful registration

**If user has no Facebook Pages:** OAuth completes but no page can be connected. System shows message: *"No Facebook Pages found on this account. Create a Facebook Page first, then reconnect."*

### Instagram Business Connector

| Step | Field / Action | Source | Type | Required |
|------|---------------|--------|------|----------|
| 1 | Initiate OAuth | User action | Click | Yes |
| 2 | Instagram Login OAuth (api.instagram.com, `instagram_business_*` scopes) | Instagram | OAuth 2.0 | Yes |
| 3 | `account_selection` | User | select (if >1 account) | Conditional: required if user has more than 1 Instagram Business account; auto-selected if exactly 1 |
| 4 | `channel_connection` record | System | auto-created | — |

**Important:** This uses the Instagram Login path (api.instagram.com endpoint, `instagram_business_*` scopes) — **not** the deprecated Facebook Login path. (Source: [[analyses/meta-integration-implementation]])

**Post-OAuth system actions (not user inputs):**
- 60-day token refresh job scheduled immediately on connection (mandatory — Instagram tokens expire at 60 days)
- App-level webhook subscription covers all connected Instagram accounts (single subscription, not per-account)
- `channel_connection.status = active` on successful setup

### WhatsApp Connector (Embedded Signup)

| Step | Field / Action | Source | Type | Required |
|------|---------------|--------|------|----------|
| 1 | Initiate Embedded Signup (JS SDK modal) | User action | Click | Yes |
| 2 | Complete Embedded Signup flow | User | WhatsApp in-modal | Yes |
| 3 | Phone number display | System | read-only display | — |
| 4 | `channel_connection` record | System | auto-created | — |

**No page/account selection step:** WhatsApp Embedded Signup returns a single WABA token and phone number. The phone number is system-extracted and displayed to the user for confirmation (read-only — not an editable input).

**Post-Embedded-Signup system actions (not user inputs):**
- Code exchange → WABA token (server-side)
- WABA token is non-expiring; no refresh job needed
- Webhook subscription registered for the WABA phone number ID
- `channel_connection.status = active` on successful registration

### LinkedIn Connector

| Step | Field / Action | Source | Type | Required |
|------|---------------|--------|------|----------|
| 1 | Initiate OAuth | User action | Click | Yes |
| 2 | LinkedIn OAuth (Marketing Developer Platform) | LinkedIn | OAuth 2.0 | Yes |
| 3 | `channel_connection` record | System | auto-created | — |

**No post-OAuth selection step** at MVP — LinkedIn OAuth grants access at the organization level; one token per connected LinkedIn organization.

**Caveat:** LinkedIn Marketing API requires a 2–4 week approval per tenant. `channel_connection.status` may show `pending_review` during this window. The UI should communicate this clearly and not block onboarding on it.

### Website Connector

| Step | Field / Action | Source | Type | Required |
|------|---------------|--------|------|----------|
| 1 | Copy JS snippet | User | read-only code block | — |
| 2 | Install snippet on tenant's site | User (external) | External action | Yes (for connector to become active) |
| 3 | `channel_connection` record | System | auto-created with `status: pending_verification` | — |
| 4 | Verification ping received | System | auto-detected | — |

**No form inputs in UI.** The snippet is system-generated (includes `tenant_id` embedded). User copies it and installs it externally. The `channel_connection` record is created immediately with `status: pending_verification`; flips to `status: active` when the system detects the first ping from the installed snippet.

**Readiness implication:** Website connector in `pending_verification` state does not count toward the "≥1 active connector" readiness condition in Stage 5. Only `status: active` connectors count.

### Stage 4 Summary: What User Actually Inputs

| Connector | User Input | Notes |
|-----------|-----------|-------|
| Facebook | OAuth consent + Page selection (if >1) | No form fields |
| Instagram | OAuth consent + Account selection (if >1) | No form fields; Instagram Login path |
| WhatsApp | Embedded Signup completion | No form fields; phone number is read-only display |
| LinkedIn | OAuth consent | No form fields |
| Website | No UI input | External JS snippet install only |

---

## Stage 5 — Readiness Check Inputs

**No user inputs.** Stage 5 is a system-run pre-flight check. The user cannot control what happens here — the system reads the current state of all upstream outputs and either passes or shows a specific failure reason pointing back to the relevant stage.

The exact readiness conditions evaluated at Stage 5 are defined in [[analyses/onboarding-flow-readiness]] (Subtask 3).

---

## Cross-Stage: consent_preference

The `consent_preference` entity (source: [[sources/2026-core-business-entities]]) is a readiness condition at Stage 5 but is **not a form input during onboarding**. Whether it is:
- User-set during onboarding (an explicit consent preferences step), or
- System-defaulted on tenant activation

...is a decision owned by Subtask 3 ([[analyses/onboarding-flow-readiness]]). If it becomes a user input, it would sit in Stage 3 or Stage 4 as an additional UI step; the field itself is a per-lead record, not a per-tenant onboarding field.

---

## Evidence

- P2-1 HYBRID classification (user intake form + LLM-strengthened description): [[analyses/execution-type-classification]]
- PersonaObject fields and LLM-inferred nature of `sales_cycle`, `scoring_weights`, `banding`, etc.: [[concepts/persona-layer]], [[analyses/persona-agent-spec]]
- Persona Agent 3 LLM steps (Onboarding Agent → ICP Agent → Signal Agent) and their inputs: [[analyses/persona-agent-spec]]
- `channel_connection` entity, OAuth flows, token lifecycle: [[analyses/channel-integration-layer]]
- Instagram Login path (api.instagram.com, NOT deprecated Facebook Login); 60-day refresh job; WhatsApp Embedded Signup; non-expiring WABA token: [[analyses/meta-integration-implementation]]
- `consent_preference` as a non-negotiable delivery prerequisite: [[sources/2026-core-business-entities]]
- Facebook Page selection post-OAuth (per-page subscribed_apps); app-level vs per-account webhook for Instagram: [[analyses/meta-integration-implementation]]

---

## Caveats & Gaps

- **`industry` controlled vocabulary:** At MVP, `industry` is free text. A future improvement would provide a dropdown or typeahead with standardized values (e.g., NAICS/SIC codes or a custom taxonomy) to improve LLM inference quality for the Persona Agent.
- **`geography_focus` standardization:** Currently free text. Could become a structured country/region selector in a future iteration to enable geo-based filtering and analytics.
- **Multi-language `business_description`:** Not specified. If tenants write in non-English (e.g., Hindi), does the LLM-strengthening step handle it? Assumed yes (Sonnet handles multilingual), but not explicitly tested.
- **Stage 3 form ordering:** `business_type` must be collected first because it controls the `target_audience` label. All other Stage 3 fields can be presented in any order. The UI must enforce this ordering constraint.
- **Facebook App Review:** Meta requires App Review for production access to Facebook Pages, Instagram Business, and WhatsApp APIs. A tenant may complete OAuth but have a connector in `status: pending_review` for 2–7 days (App Review) or up to 60 days (Business Verification). The UI must surface this state without blocking onboarding.
- **Minimum connector requirement:** Whether "any connector" suffices or a specific connector type (e.g., at least one social) is required is an open product decision. Current spec says any one active connector counts.
- **Website snippet verification timeout:** Not defined. If the tenant installs the snippet but never receives a ping (e.g., low-traffic site), `channel_connection.status` stays `pending_verification` indefinitely. A timeout or manual verification override may be needed.

---

## Follow-up Questions

- Should the `industry` field become a controlled vocabulary (dropdown) or remain free text? Free text is more flexible; controlled vocabulary produces more consistent Persona Agent outputs.
- Should `geography_focus` allow exclusions in addition to inclusions (e.g., "all of India except rural states")? Currently only positive inclusions are supported via this field; exclusions are handled by `negative_profiles`.
- Is there a character limit on the LLM-strengthened `business_description`? The Persona Agent receives it as a prompt input — excessively long descriptions could consume prompt budget.

---

## Related Documents

- [[analyses/onboarding-flow-stage-map]] — Subtask 1: stage transitions, async/sync split, failure handling per stage
- [[analyses/onboarding-flow-readiness]] — Subtask 3: exact readiness check conditions and completion criteria
- [[analyses/persona-agent-spec]] — Persona Agent inputs and 3 LLM steps (what the Stage 3 inputs feed into)
- [[analyses/channel-integration-layer]] — connector setup detail (Stage 4 backend)
- [[analyses/execution-type-classification]] — P2-1 HYBRID classification for Stage 3
- [[analyses/meta-integration-implementation]] — Facebook/Instagram/WhatsApp OAuth implementation detail
