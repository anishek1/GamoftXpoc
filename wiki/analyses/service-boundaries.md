---
type: analysis
question: "What are the service boundaries for the Lead Intelligence Engine MVP — what is a separate deployed service vs an internal module?"
date: 2026-05-19
tags: [service-boundaries, microservices, architecture, mvp, deployment, ingestion, enrichment, scoring, orchestration, reporting, onboarding, feedback]
sources_consulted:
  - "raw/assets/service_boundaries.docx"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/execution-type-classification]]"
  - "[[analyses/tech-stack-research]]"
status: COMPLETE — ingested from raw/assets/service_boundaries.docx (2026-05-19, planning audit FIX-006)
---

# Service Boundaries — Lead Intelligence Engine MVP

**Question:** What is a separate deployed service vs an internal module?
**Source document:** `raw/assets/service_boundaries.docx`
**Ingested:** 2026-05-19
**Audit fix:** FIX-006 — moved from raw/ to wiki/ to serve as an approved planning artifact for Epic 0.2 AC "service boundary doc approved"

---

## Plain-English Summary

**Why this exists:** As the system is built across microservices, the team needs a clear rule for when a capability gets its own deployment vs when it lives as a module inside another service. Without this, every capability becomes its own service (over-engineering) or everything collapses into one monolith (under-engineering). This document defines the split criteria and applies it to every capability in the system.

**How the split decision was made:** A capability is extracted as a separate service if two or more of the following differ from the surrounding code: failure domain, scaling profile, rate of change, and ownership. If they don't differ, it stays as an internal module with a clean interface — so it can be extracted later if needed.

**The result:** 7 owned services. Auth, observability, and storage are infrastructure, not services — covered by third-party tools and standard patterns.

---

## Split Criteria

A capability becomes a separate service if **two or more** of these differ from the surrounding code:

| Criterion | Question |
|---|---|
| **Failure domain** | Can this capability fail without taking the rest of the system down? Should it? |
| **Scaling profile** | Does this capability need to scale independently (e.g., high concurrency) vs rarely used (e.g., onboarding)? |
| **Rate of change** | Does this capability change often (UI, reporting) while the rest of the code is stable (scoring)? |
| **Ownership** | Does a different person or team own this capability and need independent deploy control? |

---

## The 7 Services

### 1. Ingestion Service

**Purpose:** Receives leads from all external sources (CRM webhooks, CSV uploads, API calls, forms), validates and normalizes them, and hands them off to Orchestration.

**Owns:**
- Connector logic for CRMs and webhooks
- File upload handling
- Schema validation and normalization rules
- Internal validation module

**Depends on:** Nothing internal at runtime. Publishes normalized leads for Orchestration to consume.

**Why it is a separate service:** Bad customer data and third-party connector failures must not crash scoring. Connector logic changes frequently as new sources are added.

**Split trigger for validation module:** Validation stays internal until rules become customer-configurable per tenant, or validation logic needs to be shared across multiple ingestion paths with different lifecycles.

---

### 2. Enrichment Service

**Purpose:** Looks up additional data for a lead from third-party providers, with caching, rate limiting, and per-provider cost tracking.

**Owns:**
- Third-party API clients (see [[analyses/enrichment-tools-integration]] for provider list)
- Enrichment cache
- Rate-limit policies
- Vendor cost metering

**Depends on:** External enrichment providers. Called synchronously or asynchronously by Orchestration.

**Why it is a separate service:** Vendor flakiness, rate limits, and cost per lookup are unique failure concerns. Isolating Enrichment means a vendor outage does not block scoring — stale cached data is used as a fallback.

---

### 3. Profile Service (Persona/ICP/Weights)

**Purpose:** Generates the business persona, Ideal Customer Profile, and scoring weights using LLM. Supports human review and versioned publication.

**Owns:**
- Persona/ICP prompt definitions and generation pipeline (see [[analyses/persona-agent-spec]])
- Weights generation logic (Signal Agent — see [[analyses/orchestration-layer-spec]] §3.2)
- Human review workflow
- Versioned `PersonaObject` storage (persona + ICP + weights bundled with a version ID)

**Depends on:** LLM provider (Anthropic Claude). Writes ConfigSets to shared config storage that the Scoring Agent Service reads.

**Why it is a separate service:** Runs rarely (setup + occasional refresh), is long-running, often has a human in the loop, and has a different deploy cadence from per-lead scoring. Merging with Scoring Agent would couple prompt iteration on personas to the high-frequency scoring hot path.

---

### 4. Scoring Agent Service

**Purpose:** The core intelligence agent. Takes an enriched lead plus the active ConfigSet from the Profile Service, rates the lead on five dimensions, computes the weighted score, and assigns a bucket.

**Owns:**
- Scoring prompt templates (see [[analyses/prompt-template-framework]])
- LLM call logic, retries, model routing (see [[analyses/llm-io-contract]] v1.1.0 and [[analyses/llm-operational-safeguards]])
- Per-call cost tracking
- Weighted score calculation and bucket assignment
- Reasoning trace storage

**Depends on:** LLM provider; active ConfigSet from Profile Service config store (cached locally); called by Orchestration Service with enriched lead data.

**Why it is a separate service:** High-concurrency, latency-sensitive, constantly-running profile — completely different from the batch/setup profile of the Profile Service. Also isolates LLM provider outages from the rest of the system.

---

### 5. Orchestration Service

**Purpose:** Coordinates the end-to-end flow for each lead: ingestion handoff → enrichment → scoring → result persistence → downstream notifications. Owns workflow state, retries, and failure handling.

**Owns:**
- Workflow definitions (see [[analyses/orchestration-layer-spec]] for full pipeline spec)
- Workflow state (`pipeline_stage` field — all accepted values locked)
- Retry and timeout policies
- Fan-out/fan-in logic for parallel lead processing
- Notifications module (internal for MVP)

**Depends on:** Ingestion Service, Enrichment Service, Scoring Agent Service. Writes final results to the system of record.

**Why it is a separate service:** Central coordinator that must be independently deployable. Its failure domain is unique — it must survive the failure of any individual downstream service.

**Split trigger for Notifications:** Extract when three or more notification channels exist, or when delivery guarantees (retry queues, dead-letter handling) need dedicated infrastructure.

---

### 6. Reporting Service

**Purpose:** Serves all read APIs for the UI — lead lists, score distributions, bucket breakdowns, reasoning traces, trend views.

**Owns:**
- Read models and query endpoints
- Result caching
- Read replicas or analytics stores as needed

**Depends on:** Reads from the result store populated by Orchestration. No direct dependency on scoring or enrichment at runtime.

**Why it is a separate service:** Read-heavy with a different scaling profile. Changes frequently as product needs evolve. Its downtime must not affect scoring.

---

### 7. Feedback Service

**Purpose:** Captures conversion outcomes (did the lead convert?) from CRM callbacks or manual entry.

**Owns:**
- Feedback ingestion API
- Outcome storage
- Mapping of outcomes back to scored leads

**Depends on:** External CRM callbacks. Independent of the scoring path.

**Why it is a separate service:** Even though small, losing conversion data undermines future model/weight tuning. A stable, always-available API boundary protects this data from failures elsewhere in the system.

---

### 8. Onboarding Service

**Purpose:** Guides new tenants through initial setup — collecting business description, triggering persona/ICP/weights generation via Profile Service, supporting review/edit, connecting data sources, and marking the tenant as ready for production scoring.

**Owns:**
- `onboarding_sessions` table
- Tenant state (progress through each onboarding stage — see [[analyses/onboarding-flow-stage-map]])
- `business_input_drafts` (before finalized as Profile Service inputs)

**Reads from:** Auth/tenancy provider for tenant creation. Calls Profile Service to generate and publish ConfigSets. Calls Ingestion to register connectors.

**Exposes:** UI-facing APIs for the onboarding wizard. Publishes `ClientOnboarded` event when a tenant is fully set up.

**Why it is a separate service:** Onboarding UX iterates quickly; its volume is tiny and must not share a deploy cycle with scoring. Onboarding UI changes must never destabilize the scoring hot path.

---

## Infrastructure (Not Services)

These are platform concerns covered by third-party tools, not services built by the team.

| Concern | Approach |
|---|---|
| **Authentication & tenancy** | Third-party provider (Clerk, Auth0, or WorkOS) — not built in-house. See [[analyses/security-planning]] for the locked auth policy. |
| **Observability** | OpenTelemetry + managed backend (AWS CloudWatch for Phase 1; Grafana Cloud for Phase 2). Each service emits structured events including LLM cost, prompt version, and score decisions. Domain-specific observability stays inside services for MVP. |
| **Storage** | Each service owns its own data — no standalone storage service. A shared config store backs the Profile Service → Scoring Agent handoff. The system of record backs orchestration results and reporting reads. |

---

## End-to-End Flow

### Setup / Refresh (rare — once per tenant, or on business profile change)

```
Tenant describes their business (Onboarding Service)
  → Profile Service generates persona, ICP, and weights via LLM (Pipeline 2)
  → Tenant reviews and approves
  → Profile Service publishes ConfigSet vN
  → Scoring Agent Service picks up the new active version on next config refresh
```

### Per Lead (continuous — every inbound lead)

```
Lead arrives at Ingestion Service
  → Ingestion validates, normalizes, hands off to Orchestration
  → Orchestration calls Enrichment Service (third-party data)
  → Orchestration calls Scoring Agent Service with enriched lead + active ConfigSet
  → Scoring Agent rates the lead on five dimensions, computes weighted score, assigns bucket
  → Orchestration persists the result and fires notifications
  → Reporting Service serves the result to the UI
  → When outcome is known: Feedback Service records the conversion result
```

---

## Failure Isolation Sanity Checks

| Service fails | Impact |
|---|---|
| **Ingestion Service down** | New leads are blocked at the source. Dashboards, scoring of queued leads, and feedback all continue working. |
| **Enrichment Service down** | Scoring degrades to cached or partial data. The scoring path continues — leads are scored with whatever data is available. |
| **Profile Service down** | No runtime impact on scoring. The Scoring Agent continues using the cached active ConfigSet. Only new onboardings and persona refreshes are blocked. |
| **LLM provider down** | Scoring is paused (leads enter `human_review` after retry exhaustion). Ingestion and Feedback continue accepting data. Profile Service is also blocked until provider recovers. |
| **Orchestration Service down** | Pipeline 1 pauses. No new leads are scored. All other services remain healthy; they pick up when Orchestration recovers. |
| **Reporting Service down** | UI dashboards are unavailable. Scoring, ingestion, and feedback are unaffected. |
| **Feedback Service down** | Conversion capture is paused. All scoring paths are unaffected. |

---

## Deferred Decisions (Not Split at MVP)

| Capability | Lives in (MVP) | Extract when |
|---|---|---|
| **Notifications** | Internal module in Orchestration Service | Three or more notification channels, or dedicated delivery guarantees (retry queues, dead-letter) needed |
| **Domain observability** | Infrastructure observability for MVP | Customer-facing score audit APIs, tenant-level cost reporting, or automated drift/anomaly detection are needed |
| **Validation module** | Internal module in Ingestion Service | Validation rules become customer-configurable per tenant, or shared across multiple ingestion paths with different lifecycles |

---

## Relationship to Other Planning Documents

| Document | Relationship |
|---|---|
| [[analyses/orchestration-layer-spec]] | Full spec for the Orchestration Service and Pipeline 1/2 internals |
| [[analyses/onboarding-flow-stage-map]] | Full onboarding flow owned by the Onboarding Service |
| [[analyses/llm-io-contract]] | I/O contract for the Scoring Agent Service LLM call |
| [[analyses/enrichment-tools-integration]] | Provider list and fallback chain for the Enrichment Service |
| [[analyses/security-planning]] | Auth/RBAC policy covering all services |
| [[analyses/tech-stack-research]] | Tool selection requirements per infrastructure category |
