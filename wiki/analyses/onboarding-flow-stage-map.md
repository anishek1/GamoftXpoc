---
type: analysis
question: "What are the onboarding stages from account creation to platform readiness, including dependencies, transitions, async behavior, and failure handling?"
date: 2026-05-05
tags: [onboarding, pipeline-2, tenant-setup, connector-setup, readiness-check, account-creation]
sources_consulted:
  - "[[concepts/lead-pipeline-architecture]]"
  - "[[concepts/persona-layer]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/channel-integration-layer]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[sources/2026-core-business-entities]]"
status: COMPLETE — Subtask 1 of 3 (stage map only; inputs in onboarding-flow-inputs, completion criteria in onboarding-flow-readiness); v2 fixes: event gap window, Pipeline 2 failure UX, consent_preference reference, tenant.status naming consistency
---

# Onboarding Flow — Stage Map

**Question:** What are the onboarding stages from account creation to platform readiness, including dependencies, transitions, async behavior, and failure handling?
**Date:** 2026-05-05

---

## Answer / Finding

The onboarding journey has five sequential stages. Stages 3 and 4 run partially in parallel — by design — because Pipeline 2 is asynchronous. The user is never blocked waiting for LLM processing to complete.

---

## Stage 1 — Account Creation

**What happens:**
- User registers with email and password (or SSO)
- Email verification is sent and must be completed
- User accepts Terms of Service
- A user account record is created (no tenant yet)

**Sync / Async:** Fully synchronous.

**Transition trigger:** Email verified + ToS accepted → Stage 2 unlocks.

**Failure handling:**
- Verification email not received → resend option (rate-limited)
- Duplicate email → prompt to log in or reset password
- Stage does not advance until verification is confirmed

**Resume behavior:** User can resume from email verification link at any time; account creation state is persisted after form submit.

---

## Stage 2 — Organization (Tenant) Setup

**What happens:**
- User creates an organization (maps to a `tenant` record)
- Sets organization name and a unique identifier (slug)
- Account creator is automatically assigned as tenant admin
- `tenant` record is created with `tenant.status = onboarding`

**Sync / Async:** Synchronous.

**Transition trigger:** Organization name saved and `tenant` record created → Stage 3 unlocks.

**Failure handling:**
- Duplicate organization slug → prompt to choose another
- System error on record creation → show retry option; no partial state committed
- `tenant.status` stays `onboarding` until Stage 5 completes

**Resume behavior:** If user drops off after account creation but before org setup, they land on Stage 2 on next login.

---

## Stage 3 — Business Profile & Persona Setup

**What happens (user-facing):**
- User fills out a business profile form (business type, industry, description, target audience, geography, exclusions)
- User submits the form
- System queues Pipeline 2 and shows a progress indicator: *"Setting up your scoring intelligence..."*
- User is **not blocked** — they can proceed to Stage 4 immediately

**What happens (system — async, background):**

Pipeline 2 runs in the background:

```
Business profile inputs submitted
        ↓
[Step 1] Onboarding Agent (LLM)   → PersonaObject stored
        ↓
[Step 2] ICP Agent (LLM)          → IcpDefinition stored
        ↓
[Step 3] Signal Agent (LLM)       → Signal definitions stored
        ↓
[AUTOMATION] Prompt Template built → stored in prompt_registry
```

Each step's output is the next step's input. The sequence is strictly serial inside Pipeline 2.

**Sync / Async:** User-facing step is synchronous (form submit). Backend execution is asynchronous.

**Transition trigger:** Business profile form submitted + Pipeline 2 queued → Stage 4 unlocks immediately. Pipeline 2 completion is a Readiness Check requirement (Stage 5), not a Stage 3 gate.

**Failure handling:**
- Pipeline 2 step failure (LLM error, weights don't sum to 1.0, required fields missing) → 1 retry attempt per step → if still failing: halt Pipeline 2, alert admin, notify user to review submitted information
- User is notified via notification channel when Pipeline 2 completes or fails
- Only the affected tenant's Pipeline 2 halts; other tenants are unaffected

**Resume behavior:** If user drops off after submitting, Pipeline 2 continues in the background. On return, user sees current pipeline progress.

**Pipeline 2 failure surfacing (UX rule):**
If Pipeline 2 fails while the user is on Stage 4 (connector setup) or any other stage, the system must not fail silently. Required behavior:
- A persistent error banner appears on whatever screen the user is currently on: *"Scoring setup failed — your business profile needs review."*
- Clicking the banner navigates the user back to Stage 3
- The Stage 3 form is pre-filled with their previously submitted inputs so they do not re-enter everything
- User corrects the flagged field(s) and resubmits → Pipeline 2 re-queued from Step 1

---

## Stage 4 — Connector Setup

**What happens:**
- User connects at least one external data channel
- Available channel types:
  - **Meta** (Facebook Pages + Instagram Business + WhatsApp) — OAuth / Embedded Signup flow; creates separate `channel_connection` records per surface
  - **LinkedIn** — OAuth via Marketing Developer Platform
  - **Website** — JS tracking snippet installed on tenant's site
- System registers webhook subscriptions per connected surface
- `channel_connection` records are created with `status: active` on success

**Parallel with Stage 3:** Stage 4 runs concurrently with the async portion of Stage 3. The user connects channels while Pipeline 2 runs in the background. Neither blocks the other.

**Sync / Async:** OAuth flows are synchronous (user completes redirect). Webhook registration is synchronous post-OAuth.

**Transition trigger:** At least one `channel_connection.status = active` → Stage 4 is considered sufficiently complete for Stage 5 to evaluate. User may continue adding connectors beyond this point.

**Failure handling:**
- OAuth error → user sees error, prompted to retry
- Webhook registration fails → `channel_connection.status = error`; alert shown; polling fallback activates to catch events when resolved
- One Meta surface fails (e.g., Instagram fails, WhatsApp succeeds) → remaining surfaces stay active; partial connection is valid for Stage 5 as long as at least one surface is active
- Token expiry post-setup → `channel_connection.status = expired`; user notified to reconnect; does not block Pipeline 1 from other active channels

**Resume behavior:** Partially connected channels are saved. User resumes connector setup without restarting OAuth for already-connected surfaces.

**Event gap window — what happens before Stage 5 passes:**
Webhook subscriptions go live as soon as a connector activates. This means real events (DMs, form fills) can arrive while Pipeline 2 is still running and `tenant.status = onboarding`. These events must not be dropped or trigger a scoring run against a missing PersonaObject.

Correct behavior:
- Incoming events are accepted and written as `lead` + `event` records with `pipeline_stage: captured`
- Pipeline 1 pre-flight check reads `tenant.status`; if `onboarding`, it enqueues the run but does not execute it
- When Stage 5 passes and `tenant.status = active`, the orchestrator drains the queue — all `captured` leads from the gap window are processed in order
- No event is lost; no scoring runs without a complete PersonaObject

---

## Stage 5 — Readiness Check & Activation

**What happens:**
- System runs a pre-flight check across all onboarding outputs
- Check is triggered when the user reaches this stage or when Pipeline 2 completes (whichever is later)
- If all conditions pass → `tenant.status = active` and Pipeline 1 is enabled
- User sees: *"Your platform is ready. Leads are now being scored."*

**Sync / Async:** Synchronous check; runs on demand and auto-triggers on Pipeline 2 completion.

**Transition trigger (readiness gate — detail owned by [[analyses/onboarding-flow-readiness]]):**
Both upstream conditions must converge:
1. Pipeline 2 completed successfully (all outputs persisted)
2. At least one active channel connector

`consent_preference` is **not** a readiness condition. It is a per-lead record enforced at the Pipeline 1 Consent Gate. No `consent_preference` records exist at activation time; the condition cannot fail and therefore is not a Stage 5 gate. (Resolved in [[analyses/onboarding-flow-readiness]] §3.)

**Failure handling:**
- Pipeline 2 still running → show pending state with estimated completion; check auto-retriggers when Pipeline 2 finishes
- Pipeline 2 failed → show failure reason; user directed to review and resubmit business profile (re-runs Stage 3)
- No active connector → prompt user to connect at least one channel before activation
- Partial failure (Pipeline 2 done but all connectors failed) → same connector prompt

**Resume behavior:** Stage 5 is stateless — it re-evaluates on every attempt. No partial state to recover.

---

## Stage Flow Diagram

```
Stage 1: Account Creation
    ↓ [email verified + ToS accepted]
Stage 2: Organization Setup          tenant.status = onboarding
    ↓ [tenant record created]
Stage 3: Business Profile Input ─────── queues async Pipeline 2
    ↓ [form submitted — Stage 4 unlocks]        │
Stage 4: Connector Setup ←──────────────────────┘
    │ (run in parallel)          Pipeline 2 runs in background
    │                            Events arriving here: captured,
    │                            queued, not yet scored
    ↓
Stage 5: Readiness Check
    [Pipeline 2 complete]  ────┐
    [≥1 active connector]  ────┘ → both must pass → tenant.status = active
                                         → queue drained → Pipeline 1 runs
```

---

## Evidence

- Pipeline 2 three-step structure (source: [[analyses/persona-agent-spec]])
- `tenant` record and `tenant.status` field (source: [[sources/2026-core-business-entities]])
- `channel_connection` entity and OAuth flow (source: [[analyses/channel-integration-layer]])
- Pipeline 2 must complete before Pipeline 1 can run; pre-flight check verifies PersonaObject exists (source: [[analyses/persona-agent-spec]])
- Pipeline 2 failure halts only the affected tenant; other tenants unaffected (source: [[analyses/persona-agent-spec]])
- Polling fallback activates when a connector is in error state (source: [[analyses/channel-integration-layer]])

---

## Caveats & Gaps

- **Manual channel (CSV import)** not yet designed; it would be an additional connector type in Stage 4.
- **Meta App Review** — Facebook/Instagram/WhatsApp permissions require App Review (2–7 days) and Business Verification (up to 60 days). A connector may show `status: pending_review` during this window. The platform should communicate this to the user and not block onboarding on it.
- **LinkedIn Marketing API allowlist** — requires a 2–4 week approval per tenant. Same communication pattern applies.
- **Pipeline 2 estimated completion time** — not yet defined. Depends on LLM latency for 3 sequential calls (roughly 30–90 seconds under normal conditions).
- **Multi-admin invite during onboarding** — not addressed here; assumed to be a post-activation concern unless the team decides early invite is part of Stage 2.
- **Subscription / billing step** — not modeled in the stage map. If a freemium or paid tier gate exists, it would sit between Stage 2 and Stage 3.

## Follow-up Questions

- When does the tenant admin invite additional team members — during Stage 2, or post-activation?
- Is there a timeout for onboarding? If a tenant creates an org but never completes Stage 3, when does the system clean up the partial record?
- Should Stage 4 require connectors from specific channels (e.g., at least one social connector), or is any one connector sufficient?

---

## Related Documents

- [[analyses/onboarding-flow-inputs]] — Subtask 2: required fields per onboarding stage
- [[analyses/onboarding-flow-readiness]] — Subtask 3: exact readiness check conditions and completion criteria
- [[analyses/persona-agent-spec]] — Pipeline 2 internal execution (Stage 3 backend)
- [[analyses/channel-integration-layer]] — connector setup detail (Stage 4)
- [[analyses/orchestration-layer-spec]] — Pipeline 2 orchestration and Pipeline 1 pre-flight check
- [[concepts/lead-pipeline-architecture]] — two-pipeline architecture overview
