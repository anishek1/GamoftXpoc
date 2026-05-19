---
type: analysis
question: "Define the MVP scope boundaries: what is included, what is explicitly excluded, and what are the sign-off criteria for the first production release."
date: 2026-05-19
tags: [mvp, scope, planning, sign-off, non-goals, deferred]
sources_consulted:
  - "[[sources/2026-lead-intelligence-engine-reference]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/future-optional-agents]]"
  - "[[analyses/adaptive-scoring-strategy-b2b-b2c]]"
  - "[[analyses/enrichment-tools-integration]]"
  - "[[analyses/meta-integration-implementation]]"
  - "[[analyses/security-planning]]"
  - "[[analyses/tech-stack-research]]"
status: COMPLETE
---

# MVP Scope Sign-Off — Epic 0.1

**Question:** What is in scope for MVP, what is explicitly excluded, and what must be true before the first production release is considered complete?
**Date:** 2026-05-19

This is the scope boundary document for the Multi-Tenant Adaptive Lead Intelligence Engine v2.0 MVP. It is the reference for all "is this in scope?" questions during build.

---

## 1. MVP Definition

**MVP = the system is able to score leads for all 3 POC tenants end-to-end, deliver ranked lead cards to salespeople in real time, and collect feedback that feeds back into scoring quality.**

MVP is not feature-complete. It is the smallest working system that validates the core value proposition: LLM-powered lead scoring, per-tenant, with measurable quality improvement over time.

**Three POC tenants:**
- **Gamoft** — B2B self-tenant (Gamoft's own sales pipeline)
- **Urvee Organics** — B2C (organic products, Instagram + WhatsApp)
- **Govmen** — TBD (profile requires tenant interview before onboarding can begin)

---

## 2. In Scope — MVP Capabilities

### Pipelines

| Capability | Notes |
|---|---|
| Pipeline 2 — Tenant Onboarding | Persona Agent → ICP Agent → Signal Agent → Prompt Generation; admin-assisted (not self-serve) |
| Pipeline 1 — Per-Lead Scoring | Full 6-stage pipeline: data_gather → normalise → enrich → score → bucketize → deliver |
| B2B and B2C scoring modes | `business_type` as hard mode selector; mode-specific weights, ICP, disqualification rules |
| Score decay | -10 after 7 days, -20 after 14 days, auto-COLD after 30 days |
| SLA tracking | HOT = 24h, WARM = 48h, COLD = weekly; breach alert to team lead |
| Pipeline 2 re-run | Triggered manually by admin/team lead or by feedback-driven governance |
| Crash recovery | `pipeline_stage` write-order guarantee; leads resume from last committed stage |

### Channels

| Channel | Type | Notes |
|---|---|---|
| WhatsApp | DM + Business API | Embedded Signup OAuth, WABA token per tenant |
| Instagram | DM | Instagram Login OAuth, 60-day token refresh |
| Facebook | DM | Page token (non-expiring) |
| Lead Ads | All three Meta surfaces | Enters pipeline at Stage 3 (enrichment), skips Message Parser |
| Google Sheets / CSV upload | Historical data | LLM-assisted column mapping |
| Email | Inbound | Basic parsing for lead extraction |

LinkedIn is **not** in scope at MVP.

### Enrichment

| Provider | B2B | B2C | Notes |
|---|---|---|---|
| Truecaller | ✓ | ✓ | Phone identity resolution |
| Google Places | ✓ | ✓ | Location enrichment |
| Surepass (GSTN/CIN/PAN) | ✓ | — | Indian business verification; credentials via support call |
| Apollo.io | ✓ | — | Company intelligence, email enrichment |
| Probe42 | ✓ | — | Indian SMB financials; credentials via support call |
| Tracxn | ✓ | — | Startup funding stage |
| NewsCatcherAPI | ✓ | — | Company news signals |
| Serper.dev | ✓ (fallback) | — | Google search fallback for unrecognised companies |
| IndiaMART / JustDial | ✓ | — | SMB discovery |

### Delivery

| Surface | Notes |
|---|---|
| Chat interface (primary) | Real-time ranked lead cards; HOT leads pushed immediately |
| Push notifications | HOT lead alert to salesperson |
| CRM sync | Salesforce, HubSpot; basic field mapping |
| Outbound webhooks | Fixed JSON schema; HTTPS endpoints only |
| Role-scoped dashboards | Quality dashboard (team lead), action metrics (salesperson) |
| Scheduled reports | Weekly/monthly tenant quality summary |

### Intelligence

| Capability | Notes |
|---|---|
| Persona Agent | LLM-driven business persona inference |
| ICP Agent | Ideal customer profile per B2B/B2C mode |
| Signal Agent | Signal definitions per scoring dimension |
| Rating Agent (Scoring) | Anthropic Claude Sonnet 4.6 primary; OpenAI GPT-4o via LiteLLM fallback |
| Message Parser | Haiku; DM path only for multilingual/typo-tolerant extraction |
| Prompt evaluation framework | Mandatory before any prompt goes active (draft → active transition) |
| Persona classification framework | PersonaObject full schema with inference_flags, staleness detection |

### Security and Governance

| Capability | Notes |
|---|---|
| 3-layer security (RLS + JWT + RBAC) | Clerk auth; 4 roles: admin, team_lead, salesperson, viewer |
| PII encryption at rest | AES-256-GCM on name, phone, email, address |
| Audit logging | access_log; 5-year retention |
| Lineage | pipeline_run + task_execution + lineage_record per lead per stage |
| Feedback loop | 3-step: collection → attribution → pattern detection → team lead recommendation |
| Scoring quality metrics | Score Coverage, AP1–AP4, C1–C5, AR1–AR5, 3 Global KPIs |
| Operational and business KPIs | See [[analyses/operational-business-kpis]] |
| Feature flags | JSONB in tenant_config; per-tenant capability toggles |
| Secrets management | AWS Secrets Manager (or equivalent TBD) |

### DevOps and Observability

| Capability | Notes |
|---|---|
| Structured logging with correlation_id | JSON to stdout → AWS CloudWatch Logs (Phase 1 locked — per [[analyses/tech-stack-research]]) |
| Replay/debug CLI | inspect_lineage + rescore_lead --from-stage |
| Alert system | Email (security + critical ops) + in-app (tenant-scoped) |
| Autoscaling | Per-service; implementation TBD during build |
| Automated backups | DB and workflow engine; implementation TBD |

---

## 3. Explicitly Out of Scope — MVP Non-Goals

These items are documented decisions, not oversights. Each has an unlock condition.

### Deferred Post-MVP Features

| Item | Why deferred | Unlock condition |
|---|---|---|
| **Adaptive Signal Lifecycle** (Add-ons 6/7/8) — signal integrity scoring, automated signal discovery, business-language signal UX | Requires 2–3 months of real production data to measure anything meaningful. Building on hypothetical data produces expensive random number generators. | Month 3+ with sufficient scoring history |
| **Recommendation Agent** — personalised outreach message generation | Post-scoring capability; adds value only after scoring quality is validated | After Month 3; quality metrics must be stable |
| **Workflow Agent** — lead lifecycle orchestration beyond scoring | Complex dependency on scoring quality + salesperson behaviour data | After Month 6 |
| **Self-serve tenant onboarding** | Onboarding is admin-assisted at MVP (3 known tenants) | Post-MVP when scaling to unknown tenants |
| **LinkedIn as a channel** | LinkedIn's API is more restrictive (no DM webhooks); integration complexity not justified for 3 POC tenants | Separate epic post-MVP |
| **SAML / enterprise SSO** | No POC tenant has an IdP; Clerk supports it — enable only when a tenant requests it | On-request from a tenant |
| **Govmen full onboarding** | Profile entirely TBD; blocked until tenant interview | After Govmen interview is completed |
| **Mobile app** | Web interface only at MVP | Post-MVP product decision |

### Infrastructure Deferrals

| Item | Why deferred | Upgrade trigger |
|---|---|---|
| **Redis caching** | In-memory cache is sufficient for 3 tenants | 20+ tenants or multi-instance staleness issues |
| **Silo infrastructure model** | All tenants on pool model at MVP | Premium tier tenant request |
| **Dedicated read replica per tenant** | Shared replica sufficient for MVP load | Per-tenant reporting latency becomes a problem |
| **Automated PII key rotation** | Manual rotation sufficient for 3 tenants | 10+ tenants or SOC 2 preparation |
| **Grafana Cloud (Phase 2 upgrade)** | AWS CloudWatch Logs is the MVP observability tool (locked). Grafana Cloud upgrade is eligible at Phase 2 — no code changes required, stdout→CloudWatch path is tool-agnostic. | Month 3+ or when tenant count justifies |
| **Custom webhook delivery format** | Fixed JSON schema at MVP | Per-tenant webhook format request |
| **Multi-model routing beyond primary + fallback** | Two providers (Anthropic primary, OpenAI fallback) are sufficient | Model performance divergence at scale |

### Explicit Non-Goals (never in scope unless product direction changes)

- **Scraping any website or platform** — hard policy; API-only data acquisition forever
- **Storing credentials in the database** — vault path reference only, forever
- **Returning raw PII to viewer role** — aggregated metrics only, forever
- **Cross-tenant data access** — RLS enforces this at DB level, forever

---

## 4. POC Success Criteria

These are the conditions that define MVP as complete for the 3-tenant POC. Sign-off requires all conditions to be true simultaneously for a minimum of 2 consecutive weeks.

### Technical Conditions (must be true)

| Condition | Target | Source |
|---|---|---|
| All 3 POC tenants onboarded | Pipeline 2 completed for Gamoft, Urvee Organics, Govmen | Onboarding audit log |
| Pipeline coverage | ≥ 80% of leads reach `delivered` or `human_review` in every run | `quality_snapshots` System Health |
| Bucket stability | ≥ 85% of leads score into the same bucket on consecutive runs | `quality_snapshots` System Health |
| Zero cross-tenant data leaks | No `access_log` entry showing a user accessing another tenant's data | Audit log review |
| Zero scoring failures in production | `failed` state rate < 2% over 2 weeks | `quality_snapshots` per-run metric |
| HOT SLA compliance | ≥ 80% of HOT leads contacted within 24h (at least 2 weeks of data) | AR1 metric |

### Business Conditions (must be true)

| Condition | Target | Owner |
|---|---|---|
| At least 1 HOT lead converted to a sale per tenant | Confirmed by team lead feedback | Team lead per tenant |
| Scoring Lift > 1.5 | HOT leads converting at 1.5× the rate of COLD | AP2 Discrimination Ratio |
| Salesperson feedback rate | ≥ 30% of delivered leads have feedback submitted | Feedback loop metric |
| Team lead sign-off | Each tenant's team lead confirms scores are "better than what we had before" | Manual sign-off |

### Sign-Off Process

1. Engineering lead confirms all Technical Conditions are met for 2 consecutive weeks.
2. Product owner reviews Business Conditions.
3. Each POC tenant's team lead signs off verbally or in writing.
4. Admin (Anishekh) marks MVP as complete. System transitions from POC to production.

---

## 5. Govmen Dependency

Govmen is a blocker. Nothing about Govmen's onboarding can proceed until:
1. Tenant interview is completed (business type, channels, ICP).
2. Business profile fields are collected for Pipeline 2.
3. Feature flags for Govmen are configured.

Until the interview, Govmen's onboarding is marked `blocked` and does not count toward MVP completion. Gamoft and Urvee Organics can reach POC success conditions without Govmen.

---

## Confirmed Decisions

| Decision | Basis |
|---|---|
| MVP = 3 POC tenants end-to-end with measurable quality metrics | [[sources/2026-lead-intelligence-engine-reference]] |
| Admin-assisted onboarding at MVP (not self-serve) | This document 2026-05-19 |
| Adaptive Signal Lifecycle deferred to Month 3+ | [[sources/2026-lead-intelligence-engine-reference]] §Add-ons 6/7/8 |
| No scraping — hard policy, forever | [[sources/2026-b2c-data-acquisition]] |
| LinkedIn deferred post-MVP | This document 2026-05-19 |
| POC success requires 2 consecutive weeks of conditions met | This document 2026-05-19 |
| Govmen onboarding blocked until tenant interview | [[entities/govmen]] |
