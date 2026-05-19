# Wiki Log

*Append-only. Most recent entries at top.*

---

## [2026-05-20] fix | FIX-010 — Create Enrichment-to-LLM Field Map

- Fix: FIX-010 [P2 | MAJOR | Epic 0.9]
- Files created:
  - docs/phase0/enrichment-to-llm-field-map.md (NEW — satisfies Epic 0.9 AC "enrichment-to-LLM field map completed")
- Files updated:
  - index.md — new entry added for enrichment-to-llm-field-map.md
- Content: Complete three-column trace (provider API field → EnrichedLead property → LLM INPUT_SCHEMA field + signal driven) for all 9 enrichment providers:
  - Truecaller → lead.name, lead.geography
  - Google Places → lead.geography, lead.city_tier, context.geography_tier signal
  - Apollo.io → company.name/industry/size_employees/role, fit.* signals
  - Surepass → company.registration_id, fit.company_size_fit (India B2B)
  - Probe42 → fit.company_size_fit (financial health proxy), company.size_employees override
  - Tracxn → context.account_growth_signal (funding stage + recency)
  - NewsCatcherAPI → context.account_growth_signal (news sentiment + themes)
  - IndiaMART/JustDial → fit.serviceability, fit.industry_match (SMB fallback)
  - Serper → company.name/industry (last resort), lead_completeness penalty
- Additional sections: Signal coverage by source table, field availability summary, write order and lineage note

---

## [2026-05-20] fix | FIX-011 — Lock WARM SLA Window to 48 Hours

- Fix: FIX-011 [P2 | MINOR | Epics 0.1/0.7/0.11]
- Files updated (10 files — all "2-3 days" WARM SLA references replaced):
  - wiki/analyses/action-relevance-metrics.md — AR1 definition updated to 48h; "Open decision" section removed; Target note updated
  - wiki/analyses/orchestration-layer-spec.md — §3.3 bucket table updated; §11 Confirmed Decisions row added
  - wiki/analyses/execution-type-classification.md — G-2 table row, bucket table, SLA Tracker description updated
  - wiki/analyses/delivery-integration-layer.md — lead card SLA reminder field, WARM CRM sync row updated
  - wiki/analyses/governance-observability-layer.md — AR1 metric definition updated
  - wiki/analyses/inngest-function-design.md — sla-monitor table row, directory comment, source reference updated
  - wiki/analyses/prompt-template-framework.md — WARM bucket label updated
  - wiki/analyses/mvp-scope-sign-off.md — SLA tracking row updated
  - wiki/analyses/scoring-quality-metrics.md — WARM window TBD resolved to 48h
  - wiki/analyses/tech-stack-research.md — Open decision #4 resolved
- Resolution: WARM SLA window is now 48 hours (locked) across all planning documents. AR1 metric is now calculable without this dependency. 72h option dropped.

---

## [2026-05-20] fix | FIX-013 — Lock AWS CloudWatch as Phase 1 Observability Tool

- Fix: FIX-013 [P2 | MINOR | Epic 0.11]
- Files updated:
  - wiki/analyses/observability-detail-spec.md — §1.1 log stream table updated; TBD tooling paragraph replaced with locked CloudWatch statement; Open Decisions table entry resolved
  - wiki/analyses/mvp-scope-sign-off.md — DevOps table row updated from TBD to "AWS CloudWatch Logs (Phase 1 locked)"; Infrastructure Deferrals Grafana row updated to reflect Phase 2 upgrade path
- Resolution: AWS CloudWatch (Phase 1) is now locked across both documents with a pointer to tech-stack-research.md. Grafana Cloud is documented as an eligible Phase 2 upgrade — no code changes required.

---

## [2026-05-20] fix | FIX-012 — Resolve tenant.status vs tenant.onboarding_complete Inconsistency

- Fix: FIX-012 [P2 | MINOR | Epics 0.6/0.7]
- Files updated:
  - wiki/analyses/onboarding-flow-readiness.md — Caveats & Gaps item marked RESOLVED; confirms §6.1 and §6.2 now both use `tenant.status = 'active'`
- Verification: orchestration-layer-spec.md §6.1 step 7 reads "Set tenant.status = 'active'" and §6.2 checks "Is tenant.status = 'active'?" — both already correct. `tenant.onboarding_complete` field name retired.

---

## [2026-05-20] fix | FIX-009 — Feature Flag Enforcement in Orchestration §6.3

- Fix: FIX-009 [P2 | MAJOR | Epic 0.6]
- Files updated:
  - wiki/analyses/orchestration-layer-spec.md — Added "Feature Flag Enforcement" subsection to §6.3 with: enrichment provider flag table (9 providers), enforcement pseudocode, effect on lead_completeness, configuration note
- Resolution: `tenant_config.feature_flags` is explicitly documented as loaded in step 2. Each enrichment provider call in step 6a is gated by its flag. Absent flag = disabled. Disabled providers record signals as `not_detected` and reduce `lead_completeness` proportionally.

---

## [2026-05-20] fix | FIX-008 — Wire tone and custom_rules into LLM I/O Contract

- Fix: FIX-008 [P2 | MAJOR | Epic 0.6]
- Files updated:
  - wiki/analyses/llm-io-contract.md — Added `tone` and `custom_rules` as optional fields in `persona` input object; added Design Decisions table row
  - wiki/analyses/context-construction-specification.md — Updated [CONTEXT] section description and §2.3 cache stability rules
  - wiki/analyses/prompt-template-framework.md — Added Rule 7 (custom_rules apply before score), added CONTEXT section documentation, added SALESPERSON NOTE TONE and CUSTOM RULES subsections to Sample 1 CONTEXT block, updated Sample 2 abbreviation, updated version trigger list
- Root cause: PersonaObject fields produced by Persona Agent were absent from INPUT_SCHEMA (`additionalProperties: false` would have silently dropped them). Both fields were never visible to the Rating Agent at scoring time.
- Resolution: Wired both fields in as optional, typed fields. `custom_rules` takes precedence over general rubric per Rule 7. `tone` controls `salesperson_note` communication register. Changes to either invalidate the system message cache.

---

## [2026-05-19] audit | Phase 0 Planning Audit Report

- File: docs/phase0/PLANNING_AUDIT_REPORT.md (NEW — created as output of READ-ONLY audit)
- Backlog: raw/JIRA DOCS.xlsx (Sheet1 — 11 epics, 33 stories, 99 sub-tasks)
- Files scanned: 76 .md files across wiki/ and repo root
- Conflicts found: 3 Type A (direct contradiction), 4 Type B (naming drift), 4 Type C (dependency violation), 17 Type D (AC gaps), 3 Type E (DevOps consistency), 3 Type F (LLM contract coherence)
- Total fixes: 15 (FIX-001 through FIX-015)
- Critical findings (6): prompt-template-framework stale vs llm-io-contract v1.1.0 (A-1, A-2); insufficient_signal missing from pipeline_stage locked values (A-3); agent count 4 vs 5 (B-4); 3 infra decisions unresolved in tech-stack-research.md (D-1)
- Safe to proceed immediately: Epic 0.10 (Security), Epic 0.8 (Data Acquisition), Epic 0.5 after FIX-001/FIX-002
- Notes:
  - All planning documents are OBSIDIAN_ONLY (wiki/analyses/); zero docs in /docs/phase0/ before this report
  - Strongest area: LLM I/O contract chain (Epics 0.5, 0.9 contract links); weakest area: Epic 0.2 infra decisions and Epic 0.5 prompt framework staleness
  - JIRA Epic 0.8 titles still use "scraping" terminology — action required by Anishekh before Sprint 1

---

## [2026-05-19] analysis | Epic 0.8 Data Acquisition Coverage & JIRA Rename

- File: wiki/analyses/epic-0.8-data-acquisition-coverage.md (NEW)
- Question: Epic 0.8 JIRA stories reference "scraping workflow" — does the system cover these requirements, and how should JIRA be updated?
- Tags: jira, epic-0.8, enrichment, no-scraping, data-acquisition, coverage-mapping
- Sources consulted: lead-enrichment-architecture, enrichment-tools-integration, global-data-collection-architecture, devops-controls, b2c-data-acquisition
- Notes:
  - Hard no-scraping policy: legal risk (DPDP/GDPR), reliability, maintenance cost, tenant trust
  - All 3 Epic 0.8 stories (data source strategy, scraping workflow, scraping DevOps controls) are fully covered — under different terminology
  - "Define scraping workflow" → maps to Source Registry + Company Resolver; inputs/outputs/merge logic all documented
  - "Define scraping DevOps controls" → fully in devops-controls.md §0.8.1–0.8.3 (scheduler, throttling, failure logging)
  - Full rename table: Epic title + 8 story/sub-task titles
  - Action required: Anishekh to update JIRA story titles before Sprint 1 planning

---

## [2026-05-19] analysis | Core Use Cases — MVP Launch

- File: wiki/analyses/core-use-cases.md (NEW)
- Question: What are the 3 core use cases the platform must support for initial launch, with inputs, outputs, and stakeholders?
- Tags: use-cases, mvp, b2b, b2c, smb, noise, pipeline1, stakeholders
- Sources consulted: global-data-collection-architecture, orchestration-layer-spec, rating-agent-spec, mvp-scope-sign-off, delivery-integration-layer, onboarding-flow-stage-map
- Notes:
  - UC1 High-Intent B2B Enterprise: HOT path, all 13 pipeline steps, salesperson receives HOT card + 24h SLA; stakeholders: salesperson, CRM, team lead, eng lead
  - UC2 SMB/Fragmented Lead: B2B confirmed via business_ownership signal despite no company name; Apollo/MCA miss → company_verified: false; COLD card with qualification prompt; upgrade path via GST → re-score
  - UC3 Low-Signal/Noise: Message Parser returns proceed: false; pipeline stops at Step 2; no enrichment API called; no salesperson card; discard logged in intake_event_log
  - Cross-use-case stakeholder matrix added
  - Covers JIRA Epic 0.1 "Define core use cases" acceptance criteria (3 use cases with inputs, outputs, stakeholders)
  - Also covers previously flagged gap: "Document low-intent lead journey"

---

## [2026-05-19] analysis | Operational and Business KPIs — Epic 0.1

- File: wiki/analyses/operational-business-kpis.md (NEW)
- Question: What are the operational KPIs (system health) and business KPIs (value delivery), and how are they measured?
- Tags: kpis, operational, business, metrics, monitoring, dashboard, mvp
- Sources consulted: 2026-lead-intelligence-engine-reference, scoring-quality-metrics, governance-observability-layer, devops-controls, observability-detail-spec, mvp-scope-sign-off, service-scaling-strategy, llm-operational-safeguards
- Notes:
  - 3-layer KPI architecture: Operational (OP1–OP7, engineering) → Scoring Quality (AP/C/AR, existing doc) → Business (BK1–BK6, product/management)
  - OP1 Lead Processing Latency p95: target <120s, alert >300s; measured from pipeline_run timestamps
  - OP2 LLM Call Latency p95: target <8s, alert >15s; measured from task_execution.duration_ms at score stage
  - OP3 Pipeline Success Rate: target ≥98%, alert <95% over 1h; from quality_snapshots (not raw pipeline_run)
  - OP4 Enrichment Provider Availability: per-provider targets (T1 ≥95%, T2 ≥90%, T3 ≥85%); from enrichment_quota + task_execution
  - OP5 Background Job Completion Rate: alert on any job missing 2 consecutive windows; sla_breach_check → Critical if missing
  - OP6 Cost per Lead: target <$0.05, alert >$0.10; from token usage logs + enrichment invoices
  - OP7 Queue Depth: alert >200; from workflow engine queue (tool TBD)
  - BK4 Scoring Lift confirmed = AP2 Discrimination Ratio (same metric, different audience)
  - BK5 Salesperson Adoption ≥30% is prerequisite for BK3/BK4 statistical reliability
  - Full mapping: every MVP sign-off condition from mvp-scope-sign-off §4 traced to specific KPI + query

---

## [2026-05-19] analysis | MVP Scope Sign-Off — Epic 0.1

- File: wiki/analyses/mvp-scope-sign-off.md (NEW)
- Question: Define MVP scope boundaries: what is included, explicitly excluded, and sign-off criteria for first production release
- Tags: mvp, scope, planning, sign-off, non-goals, deferred
- Sources consulted: 2026-lead-intelligence-engine-reference, orchestration-layer-spec, future-optional-agents, adaptive-scoring-strategy-b2b-b2c, enrichment-tools-integration, meta-integration-implementation, security-planning, tech-stack-research
- Notes:
  - MVP definition: 3 POC tenants (Gamoft B2B, Urvee Organics B2C, Govmen TBD) end-to-end with measurable quality improvement
  - In scope: Pipeline 1 + Pipeline 2, 6 channels (WA/IG/FB DM/Lead Ads/Sheets/Email), 9 enrichment providers, all delivery surfaces, full security/governance, DevOps
  - LinkedIn deferred; Adaptive Signal Lifecycle deferred to Month 3+; Recommendation Agent Month 3+; Workflow Agent Month 6+; self-serve onboarding post-MVP
  - Hard non-goals (forever): no scraping, no credentials in DB, no raw PII to viewer role, no cross-tenant access
  - POC success requires 2 consecutive weeks: ≥80% pipeline coverage, ≥85% bucket stability, <2% failure rate, ≥80% HOT SLA, Scoring Lift >1.5, team lead sign-offs
  - Govmen dependency: full onboarding blocked until tenant interview; Gamoft + Urvee Organics can reach POC success without Govmen

---

## [2026-05-19] analysis | DevOps Controls — Epics 0.6–0.9

- File: wiki/analyses/devops-controls.md (NEW)
- Tags: devops, feature-flags, monitoring, dashboard, throttling, caching, scheduler, alerting, onboarding
- Notes:
  - 0.6 Onboarding: feature_flags JSONB on tenant_config (no external flag service); 3-step rollout (Gamoft → 1 POC → all → remove); Pipeline 2 failure alert spec with action_required field; 8 onboarding-specific audit log events (flag changes most important)
  - 0.7 Orchestration: ops dashboard (10 panels, real-time + quality_snapshots) vs tenant quality dashboard (7 panels, quality_snapshots only); job tracking primary = workflow engine UI; background job drift detection via missing log event within 2× window
  - 0.8 Data Acquisition: enrichment is per-lead (no batch); 8 background jobs with schedules; enrichment_quota Postgres table with 90% threshold skip; daily enrichment health snapshot job; provider success rate <50% → High alert
  - 0.9 Context Construction: in-memory TTLCache (cachetools, 15-min TTL, no Redis at MVP); cache key = (tenant_id, prompt_template_version); force-flush CLI with Postgres NOTIFY; prompt version rollback procedure; validation failure rate >5% → High alert; logged to app log + task_execution

---

## [2026-05-19] analysis | Observability Detail Specification — Epic 0.11

- File: wiki/analyses/observability-detail-spec.md (NEW)
- Tags: observability, logging, tracing, alerting, autoscaling, backup, recovery
- Sources consulted: governance-observability-layer, orchestration-layer-spec, service-scaling-strategy, tech-stack-research, llm-operational-safeguards, security-planning
- Notes:
  - Step-level logging: full structured JSON log event catalog for Pipeline 1 (7 stages × N events), Pipeline 2 (4 stages), and 4 background jobs; PII-never-in-logs rule enforced
  - Trace correlation: correlation_id = pipeline_run.id propagated via HTTP X-Correlation-ID header + Temporal context + every log line and lineage row; CloudWatch Logs Insights query pattern documented
  - Replay/debug: inspect_lineage CLI + rescore_lead --from-stage CLI; dry-run batch_rescore for staging prompt testing; per-stage replay avoids wasting enrichment API quota
  - Alert thresholds: 8 operational alerts (Critical→Low, named owner + response SLA), 7 infra alerts, 4 post-Month-1 quality alerts; alert delivery resolved via security-planning
  - Autoscaling: Ingestion 100 req/min/task (max 10 tasks); Orchestration 70% CPU (max 8, 600s scale-in cooldown); Reporting 60% CPU (max 4); Aurora ACU 0.5–4
  - Backup/recovery: Aurora 35-day PITR + monthly pg_dump → S3 Glacier; Temporal daily pg_dump → S3 (7-day retention); RTO 30s / RPO 5min; full recovery runbook for DB failure

---

## [2026-05-19] analysis | Security Planning — 5 Open Decisions Resolved

- File updated: wiki/analyses/security-planning.md
- All 5 previously open decisions are now locked:
  - PII key rotation: manual at MVP; automate post-Month 3 or at 10+ tenants
  - Alert delivery: email (SES/Resend) at MVP; Slack webhook post-Month 1
  - Data retention: 2yr leads/pipeline/feedback, 5yr access_log, 1yr quality_snapshots (DPDP-compliant; must appear in privacy notice before Tenant 1 onboarding)
  - lineage_record access: CLI script (inspect_lineage) at Pipeline 1 build time; promote to admin API in Month 2
  - Clerk session: email+password + Google OAuth both enabled; no magic link, no SAML at MVP

---

## [2026-05-19] analysis | Security Planning — Epic 0.10

- File: wiki/analyses/security-planning.md (NEW)
- Question: Full security spec: auth, RBAC, API access rules, input sanitization, encryption policy, secrets management, PII masking, prompt logging sanitization, audit logging
- Tags: security, auth, rbac, jwt, clerk, pii, encryption, secrets, audit, sanitization
- Sources consulted: governance-observability-layer, tech-stack-research, context-construction-specification, delivery-integration-layer, channel-integration-layer, enrichment-tools-integration, llm-operational-safeguards
- Notes:
  - Story 1 (Auth + RBAC): Clerk Organizations API confirmed as auth provider; JWT claims (sub/org_id/org_role); FastAPI middleware pattern; 1-hour access token; full 4-role permission matrix; endpoint-level RBAC table for all API surfaces
  - Story 2 (Data + API protection): Pydantic v2 extra="forbid" as input sanitization layer; E.164 phone validation; EmailStr; SQL injection not applicable (ORM only); HMAC-SHA256 two-step webhook validation; AES-256-GCM PII encryption (application layer, key in Secrets Manager); TLS 1.2+ everywhere; full 15-credential secrets vault inventory with vault path naming convention and rotation triggers
  - Story 3 (LLM data safety): PII-in-user-message-only rule locked; per-enrichment-call minimum identity field table; prompt log sanitization (REDACTED substitution for all log output); lineage_record.input_snapshot stored encrypted, admin-only; audit log schema and full event trigger list; 5 security-specific alert conditions
  - 5 open decisions remain: PII key rotation method, alert delivery channel, data retention per jurisdiction, lineage admin access UI, Clerk session UX

---

## [2026-05-18] analysis | 6 Specification Documents — Context Construction, Prompt Orchestration, LLM I/O Contract, Adaptive Scoring B2B/B2C, Prompt Evaluation, Persona Classification

- Files created/updated:
  - wiki/analyses/context-construction-specification.md (NEW)
  - wiki/analyses/prompt-orchestration-framework.md (NEW)
  - wiki/analyses/llm-io-contract.md (REVISED — v1.1.0)
  - wiki/analyses/adaptive-scoring-strategy-b2b-b2c.md (NEW)
  - wiki/analyses/prompt-evaluation-framework.md (NEW)
  - wiki/analyses/persona-classification-framework.md (NEW)
- Notes:
  - context-construction-specification: Defines Prompt Layer vs Orchestrator ownership boundary, static/dynamic split, signal ordering rule (alphabetical for cache stability), pre-send validation gate (8 checks), PII-in-user-message-only rule, tiered token budgets, PersonaObject 15-min TTL, 3-identifier lineage (prompt_template_version + persona_version + schema_version)
  - prompt-orchestration-framework: Resolves TBD on prompt storage (hybrid: code for system-level, DB for tenant-level), specifies prompt_registry data model, version lifecycle state machine (draft→active→deprecated), rollback procedure, MAJOR version backward-compatibility requirement, prompt template generation automation step
  - llm-io-contract: Revised v1.1.0 — resolves context_inputs required-field contradiction (fields made optional, cross-field rules enforce variant-conditional requirements), fixes behavior.revisit_count minimum to 0 (Lead Ad entries), adds COMPANY_B2B_REQUIRED cross-field rule, adds additionalProperties:true on signal dimension objects for tenant extensibility, retains reasoning-as-structured-object and recommended_action-enum decisions
  - adaptive-scoring-strategy-b2b-b2c: Defines business_type as hard mode selector (not hint), signal applicability enforcement, mode-specific default weights (B2B 25/25/20/20/10 vs B2C 20/25/20/25/10), mode-specific ICP structures (company fields vs demographic fields), mode-specific lead completeness formulas (B2B penalises missing company data; B2C does not), mode-specific disqualification rules, mode-specific default bucket thresholds (B2B 80/55, B2C 75/50), enrichment pipeline step gating by mode, Message Parser extraction fields by mode
  - prompt-evaluation-framework: Defines mandatory evaluation before draft→active transition, 6 evaluation dimensions (4 automated + 2 human), golden test set specification (10 required categories, test case format, B2B/B2C coverage), automated check thresholds (100% schema compliance, ≥90% bucket accuracy), team lead review procedure (5–10 case sample), regression detection thresholds, instruction-following checks (hallucinated signals, not_detected misuse, markdown in output), 5 online monitoring signals that trigger re-evaluation
  - persona-classification-framework: Full PersonaObject schema with inference_flags, IcpDefinition schema by mode, persona quality criteria (completeness + signal coverage + ICP specificity), minimum signal coverage requirements (Fit≥3, Intent≥5, Engagement≥4, Behaviour≥3, Context≥2), custom_rules format and enforcement rules, tone field specification (affects salesperson_note wording only), inference confidence tracking, persona change classification (Minor vs Major tier), staleness detection signals, how personas drive lead classification at scoring time

---

## [2026-05-16] analysis | Enrichment Tools Integration — Surepass, Probe42, Tracxn, NewsCatcherAPI, Serper

- File: wiki/analyses/enrichment-tools-integration.md
- Question: How do Surepass, Probe42, Tracxn, NewsCatcherAPI, and Serper.dev integrate into the current lead intelligence pipeline?
- Tags: enrichment, surepass, probe42, tracxn, newscatcher, serper, pipeline-1, source-registry, normalised-event, b2b-investigation
- Sources consulted: [[wiki/analyses/lead-enrichment-architecture]], [[wiki/analyses/global-data-collection-architecture]], [[wiki/analyses/orchestration-layer-spec]], [[wiki/analyses/signal-detection-rule-spec]], [[wiki/analyses/tech-stack-research]], [[wiki/analyses/inngest-function-design]]
- Notes:
  - 5 tools mapped to specific gaps in existing stack: Surepass (managed Indian govt API gateway, replaces brittle direct GSTN/MCA calls), Probe42 (Indian SMB financial intelligence not in Apollo), Tracxn (startup funding stage signal — no equivalent in current stack), NewsCatcherAPI (zero news signals in current stack; news as leading indicator), Serper.dev (Google Custom Search replacement; last-resort fallback for micro-businesses with zero enrichment)
  - All 5 tools treated as confirmed architecture; endpoint credentials to be obtained after vendor support calls
  - Tracxn integration fully verified from official Postman docs: POST /api/2.2/companies/search, /api/2.2/companies, /api/2.2/transactions; accessToken header; 100 req/hr playground limit
  - NewsCatcherAPI fully verified from official docs: base URL https://v3-api.newscatcherapi.com/api; x-api-token auth; two-call strategy (aggregation_count → search only if total_hits > 0)
  - Surepass architecture: managed gateway for 240+ Indian govt APIs; confirmed base URL kyc-api.surepass.io/api/v1; endpoints follow /corporate/{gstin,cin,pan-to-company-details} pattern; credentials via onboarding
  - Probe42 architecture: 21M Indian companies; Probe Score 1–5; financials, court records, ROC charges, EPFO headcount; credentials via support call
  - Serper.dev: $50/50K queries; endpoints /search, /news, /maps; Google Custom Search replacement (new customer signups closed 2025, shutdown Jan 2027)
  - New NormalisedEvent fields: 8 Surepass fields, 11 Probe42 fields, 11 Tracxn fields, 8 NewsCatcherAPI fields, 9 Serper fields
  - Source Registry updated: all 5 tools inserted at correct priority positions for IN jurisdiction B2B path
  - Cost model updated: B2C ~$0.025–0.04/lead; B2B India full investigation ~$0.10–0.20/lead
  - Pending: Surepass support call (endpoints + sandbox + pricing), Probe42 support call (API v2 docs + sandbox), Serper.dev free tier signup

---

## [2026-05-16] ingest | Lead Ingestion Strategy

- File: raw/assets/Lead_Ingestion_Strategy.docx
- Wiki page: [[wiki/sources/2026-lead-ingestion-strategy]]
- Entities updated: none (no new project-specific entities)
- Concepts created: [[wiki/concepts/lead-ingestion-sources]], [[wiki/concepts/two-stage-lead-filtering]]
- Concepts updated: [[wiki/concepts/lead-pipeline-architecture]] (Ingestion Layer section added), [[wiki/concepts/feedback-loop]] (ingestion-level classifier feedback section added)
- Notes:
  - 4 Phase 0 sources: email (unique inbound address, template parsing, no per-email LLM), WhatsApp Business (API only, two-stage filter), Instagram DMs (same + sender profile signals, voice transcription), Google Spreadsheet (service account, 15-min poll, LLM column mapping, watermark column)
  - Two-stage filtering: rule stage (~30–40% eliminated) → LLM classification (LEAD/EXISTING_CUSTOMER/NOISE/UNCLEAR); default-to-LEAD calibration
  - Cross-source: normalization adapters, phone+email dedup, immutable intake event log, tenant "not a lead" classifier feedback
  - Open question flagged: ingestion LLM classifier vs Message Parser (Haiku) in Pipeline 1 — same invocation or two separate LLM calls on DM path?

## [2026-05-16] ingest | B2C Data Acquisition: How We Will Get Order and Chat History

- File: raw/assets/B2C_Data_Acquisition.docx
- Wiki page: [[wiki/sources/2026-b2c-data-acquisition]]
- Entities updated: [[wiki/entities/urvee-organics]] — mentioned as primary B2C POC tenant
- Concepts created: [[wiki/concepts/b2c-data-acquisition]]
- Concepts updated: [[wiki/concepts/lead-pipeline-architecture]] (B2C data acquisition referenced in Ingestion Layer section)
- Notes:
  - 4-method hierarchy: Official APIs (Shopify/WooCommerce/BigCommerce/Magento/WhatsApp/Instagram/Messenger/Stripe/Razorpay; Phase 1: Amazon/Flipkart/Meesho seller-only) → Webhooks → CSV upload (LLM column mapping, monthly reminders) → Scraping (explicitly excluded)
  - Hard no-scraping policy: ToS violation, legal exposure, GDPR, account suspension risk
  - Data boundary locked to tenant's own ecosystem; cross-retailer customer history inaccessible by design
  - Behavioral signals from own data (LTV, recency, frequency, affinity, responsiveness) stated as sufficient for B2C scoring

---

## [2026-05-13] analysis | Inngest Function Design — Lead Intelligence Engine

- File: wiki/analyses/inngest-function-design.md
- Question: How should the Lead Intelligence Engine be implemented as Inngest functions?
- Tags: inngest, pipeline-1, pipeline-2, orchestration, background-jobs, scheduled, crash-recovery, concurrency
- Sources consulted: orchestration-layer-spec, onboarding-flow-stage-map, onboarding-flow-readiness, tech-stack-research, service-scaling-strategy, governance-observability-layer, scoring-quality-metrics, score-decay, action-sla, feedback-loop, 2026-core-business-entities
- Source docs: Entity_Reference_Guide.docx, intelligence_layer_design (1).docx, kpi-reference.docx, nine_business_impact_kpis.docx, service_boundaries.docx, er_diagram_full.png
- Notes:
  - 8 Inngest functions created covering all workflows
  - Pipeline 2 (onboarding): serial 5-step LLM workflow; concurrency key = tenant_id (limit 1); explicit 2-attempt retry per LLM step; activation drains captured-lead queue
  - Pipeline 1 data-gather: pre-flight → parallel channel fetch (12s timeout) → dedup → fan-out via sendEvent
  - Pipeline 1 lead-processor: DM path (Pre-Filter + Haiku) + Lead Ad path (enters at Step 2); step.waitForEvent for 24h clarification timeout; per-tenant concurrency cap (default 2)
  - Score decay cron: daily 02:00 UTC; -10@7d, -20@14d, auto-cold@30d; lineage writes wrapped non-fatal
  - SLA monitor cron: hourly; alerts team lead on HOT/WARM breaches; writes to alert_incident
  - Quality metrics: per-run (pipeline/run.complete event), weekly (Monday 00:00), monthly (1st, requires ≥100 outcomes); all reads from quality_snapshots only
  - Pipeline2 rerun check: bi-weekly cron; proactive check-in + AP2 discrimination ratio signal; "system proposes, team lead approves" enforced
  - Key caveat: implementation uses TypeScript/Next.js; tech-stack-research locks Python — team must decide on SDK language

## [2026-05-07] analysis | Client Configuration Schema — Default and Override Settings (Subtask 3 of 3)

- File: wiki/analyses/client-config-schema-defaults.md
- Question: What are the default values and client override behavior for operational settings in the client configuration schema?
- Tags: client-config, schema, defaults, tiering, tenant-config, operational-limits, overrides, system-config
- Sources consulted: service-scaling-strategy, llm-operational-safeguards, rating-agent-spec, execution-type-classification, orchestration-layer-spec, sources/2026-core-business-entities, governance-observability-layer
- Notes:
  - Two-entity model: tier lives on tenant (identity/commercial); operational limits live in tenant_config (separate FK entity); three reasons documented (RBAC, change frequency, audit trail)
  - Group 1 (Pipeline Execution): scoring_concurrency_cap (2/3/5), pipeline_runs_per_hour (20/50/null); Haiku semaphore scope gap flagged (Caveat 3)
  - Group 2 (LLM Cost Controls): daily_llm_cost_cap_usd Basic=5.00, Standard/Premium=[TBD]; tenant-can-lower pattern; rejection-over-silent-cap for raise requests; alert 80%, hard stop 100%, midnight UTC reset
  - Group 3 (Token Budget): token_budget_per_lead (4000/8000/null); 16K hard block (PromptTooLargeError); touchpoints-first truncation strategy
  - Group 4 (API Rate Limits): api_requests_per_minute (30/100/500); enforced at API gateway layer
  - Group 5 (Reporting): scheduled_reports (none/weekly_digest/daily_digest+custom) — tier-locked, no override path
  - Group 6 (Quality Gate): needs_review_threshold (float 0.0-1.0, default [TBD]); overridable by team lead; affects Output Schema Layer routing only; two candidates 0.60/0.75 documented
  - Group 7 (Infrastructure): infra_model (pool/pool/pool-or-silo), read_path (shared/shared/dedicated) — tier-locked; silo flag is migration eligibility marker, not immediate toggle (Caveat 6)
  - Group 8 (LLM/Prompt Config): llm_model_override (null/null/null), active_prompt_version (null/null/null) — both open decisions; platform admin only
  - Tier defaults matrix: complete table all 11 fields × 3 tiers
  - Override enforcement: resolution order diagram (tier change → populates defaults → per-field override within bounds); role permissions table (5 roles × all fields); tenant_config NOT cached (read fresh at P1-0d) vs PersonaObject 15-min TTL
  - system_config: 7 system-wide fields (system_monthly_cost_cap_usd=$100, cost_alert_threshold_pct=0.80 [PROPOSED configurable — source documents as constant], default_tier=basic, default_llm_model=claude-sonnet-4-6, cost_anomaly_multiplier=3.0× [PROPOSED configurable — source documents as constant], persona_cache_ttl_seconds=900 [PROPOSED configurable — source documents as constant], max_prompt_tokens=16000 [not configurable])
  - provider_pricing_config: per-model pricing table entity (6 fields: provider, model, input/cached/output price per 1M tokens, effective_from/to)
  - Entity Gaps: 4 new entities (tenant_config, system_config, provider_pricing_config, prompt_registry) + 1 field addition (tenant.tier) needed in 32-entity catalog
  - 6 open decisions: Standard/Premium daily cost caps; needs_review_threshold default; Haiku concurrency semaphore scope; LLM model config scope (global vs per-tenant); prompt storage (git vs DB); silo migration workflow ownership
  - Three-pass draft→gaps→refine cycle completed; advisor call timed out; proceeded with own analysis
  - POST-FILING CORRECTIONS ROUND 1 (same session): (1) tenant.status enum corrected — suspended/churned removed (not in vault; state machine is onboarding→active only); (2) prompt_registry added as 4th missing entity gap (absent from 32-entity catalog, present in 6+ docs); (3) needs_review_threshold routing bands clarified — source ambiguity between fixed <50% floor and TBD configurable threshold (0.60/0.75) now documented explicitly; (4) cached_input_token_price_usd description corrected to match source language ("90% less" not "0.1×")
  - POST-FILING CORRECTIONS ROUND 2 (same session — systematic invented-detail audit): (5) scoring_concurrency_cap override minimum removed ("minimum of 1" not in vault); (6) pipeline_runs_per_hour queue-not-reject claim marked [PROPOSED] (queue behavior only sourced for cost caps, not rate limits); (7) daily_llm_cost_cap_usd override minimum removed ($0.50 floor not in vault); (8) tenant-can-lower / platform-controls-ceiling pattern marked [PROPOSED] (vault only says "configurable per tenant", not who or in which direction); (9) token_budget_per_lead override minimum removed ("minimum of 1,000" not in vault); (10) api_requests_per_minute API gateway enforcement point marked [PROPOSED] (enforcement architecture not specified in vault); (11) Role Permissions table given prominent [PROPOSED] header note (4-role model is sourced; per-field cell assignments are not); (12) rejection-over-silent-cap rationale marked [PROPOSED design principle]; (13) cost_alert_threshold_pct / cost_anomaly_multiplier / persona_cache_ttl_seconds "Mutable By" column marked [PROPOSED configurable] (all three documented as constants in sources, not configurable settings); (14) explanatory note added to system_config section distinguishing sourced constants from proposed-configurable fields; (15) log entry mismatch fixed (fallback_llm_model and onboarding_timeout_minutes replaced with actual fields); (16) entity gap count corrected to "four entities" in §Entity Gaps body text

---

## [2026-05-07] analysis | Client Configuration Schema — Persona and Scoring Preference Fields (Subtask 2 of 3)

- File: wiki/analyses/client-config-schema-persona-scoring.md
- Question: What are the persona and scoring preference fields in the client configuration schema — dimension weights, bucket thresholds, output preferences, and custom rules?
- Tags: client-config, schema, persona-layer, scoring-weights, banding, signal-weights, recommended-action
- Sources consulted: persona-agent-spec, rating-agent-spec, llm-io-contract, concepts/persona-layer, concepts/signal-types, service-scaling-strategy
- Notes:
  - Group 1 (Dimension Scoring Weights): scoring_weights.{fit, intent, engagement, behaviour, context}; defaults 0.25/0.25/0.20/0.20/0.10; must sum to 1.0 ± 0.001; enforced at Persona Agent output and Pipeline 1 pre-flight (PersonaInvalidError → human_review); sub-score ceilings 25/25/20/20/10 at defaults — hardcoded in llm-io-contract (spec bug if weights overridden)
  - Group 2 (Bucket Threshold Configuration): banding.hot_min=80, warm_min=55, cold_max=54; cold_max always = warm_min−1 (stored explicitly but derivable); THRESHOLD_ORDER invariant (warm_min < hot_min); Output Schema Layer enforces banding — banding always wins over LLM bucket claim
  - Group 3 (Output Tone Preference): tone string; present in PersonaObject but ABSENT from llm-io-contract INPUT_SCHEMA `persona` object — wiring gap flagged; three resolution paths noted; no invented downstream behavior
  - Group 4 (Custom Scoring Rules): custom_rules string[]; same INPUT_SCHEMA gap as tone; also used by Persona Agent for uncertainty flagging (null notes pattern)
  - Group 5 (Signal-Level Weights): signal.weight_within_dim; per-dimension sum-to-1.0 constraint; ONLY field editable without a full Persona Agent re-run; asymmetry explicitly documented
  - Group 6 (Output Format Constraint): recommended_action 7-value enum (call_immediately, schedule_demo, send_pricing_deck, follow_up_scheduled, send_qualifying_message, nurture, archive); per-lead LLM output — NOT a PersonaObject field; B2C coverage gap noted
  - Change Management Summary table: 6 rows covering all groups and their change paths
  - Three-level scoring config architecture (dimension weights → signal weights → bucket thresholds) documented as ASCII diagram
  - 5 Caveats: (1) sub-score ceiling inconsistency with per-tenant weight overrides, (2) tone/custom_rules not wired in INPUT_SCHEMA, (3) recommended_action B2C gap, (4) no UI/API for direct signal weight edit, (5) cold_max redundant storage
  - Advisor consulted before drafting; sub-score inconsistency surfaced as spec bug; tone/custom_rules gap confirmed; three-pass draft→gaps→refine cycle completed

---

## [2026-05-06] analysis | Client Configuration Schema — Business Profile Fields (Subtask 1 of 3)

- File: wiki/analyses/client-config-schema-business-profile.md
- Question: What are the business profile fields in the client configuration schema — covering industry, business model, geography, and target market?
- Tags: client-config, schema, business-profile, onboarding, tenant-setup, persona-layer
- Sources consulted: onboarding-flow-inputs, persona-agent-spec, concepts/persona-layer, sources/2026-core-business-entities, concepts/signal-types
- Notes:
  - Group 1 (User-Collected, Stage 3): 6 fields — business_type (enum B2B|B2C|Hybrid), industry (string 3-100 chars), business_description (string 150-2000, dual storage), target_audience (string[], ≥1 entry, label adapts per business_type), geography_focus (string[], ≥1 entry, target market not client location), negative_profiles (string[], optional)
  - Group 2 (LLM-Inferred, Persona Agent Step 1): sales_cycle, ticket_size, decision_complexity, product_lines — stored in personas entity; never user-editable
  - Group 3 (LLM-Inferred, Persona Agent Step 2 / IcpDefinition): icp_description, target_segment, company_size_preference, priority_signals, disqualifying_signals, buying_triggers, icp_examples — stored in ideal_customer_profile; disqualifying_signals feeds Pipeline 1 Disqualification Gate directly
  - Group 4 (System-Generated): business_profile_id, tenant_id, profile_status (draft|active|archived), profile_version (integer, increments on Persona Agent re-run only), created_at, updated_at, persona_agent_run_id
  - Design rules documented: business_type as canonical business model (operational model LLM-inferred from business_description, not a separate field); business_description dual storage (raw → business_profile_source, strengthened → business_profile); geography_focus captures target market geography not client location; target_audience form label maps to target_roles in PersonaObject (B2C legacy naming caveat)
  - Advisor consulted before drafting; confirmed no invented fields; three-pass draft→gaps→refine cycle completed

---

## [2026-05-05] correction | Orchestration Layer + Delivery Layer — Integration layer placement fixed

- Files: wiki/analyses/orchestration-layer-spec.md, wiki/analyses/delivery-integration-layer.md
- Issues fixed:
  1. Section 2 diagram (orchestration-layer-spec): Delivery and Integration Layer connector was visually ambiguous — a floating `│` at col 36 between both pipeline boxes implied Pipeline 2 also feeds the Delivery Layer. Fixed: connector realigned to col 53 (matching Pipeline 1's `┬` output); `▼` in Delivery Layer header repositioned accordingly. Label added: "scored leads (Pipeline 1 only)".
  2. Two distinct integration layers were not documented as a system fact. Added reading note in orchestration-layer-spec §2 and scope note in delivery-integration-layer §1 making clear: Channel Integration Layer (input side, upstream of Pipeline 1, see channel-integration-layer) and Delivery and Integration Layer (output side, post-Bucketize, downstream of Pipeline 1) are separate layers serving opposite ends of the pipeline.
- Pages touched: orchestration-layer-spec (Section 2 diagram + reading note), delivery-integration-layer (Section 1 scope note)

---

## [2026-05-05] analysis | Onboarding Flow — Completion Criteria (Subtask 3 of 3)

- File: wiki/analyses/onboarding-flow-readiness.md
- Question: What are the exact conditions for onboarding completion and Pipeline 1 activation?
- Tags: onboarding, pipeline-1, pipeline-2, tenant-setup, readiness-check, consent, activation
- Sources consulted: persona-agent-spec, orchestration-layer-spec, channel-integration-layer, onboarding-flow-stage-map, lead-pipeline-architecture, core-business-entities
- Notes:
  - Two conditions required simultaneously: (1) Pipeline 2 fully completed (PersonaObject + IcpDefinition + signal definitions + prompt template all persisted); (2) ≥1 channel_connection.status = active
  - consent_preference: RESOLVED — not a Stage 5 condition; per-lead record; enforcement point is Pipeline 1 Consent Gate; no records exist at activation time; condition cannot fail → not a condition
  - tenant.status state machine: onboarding (Stage 2) → active (Stage 5 pass); one-way; stays active if connectors go inactive after activation
  - Activation effects in order: (1) tenant.status = active (atomic CAS write) → (2) queue drain FIFO by arrival_at → (3) Pipeline 1 enabled → (4) user notification
  - Pipeline 2 re-run after activation: tenant.status unaffected; Persona Engine 15-min TTL cache invalidates on new PersonaObject; no Pipeline 1 disruption
  - Stage 5 vs Pipeline 1 pre-flight check: explicitly distinguished with comparison table; pre-flight is per-run, does not check connectors
  - Named inconsistency: orchestration-layer-spec §6.1 step 7 and §6.2 use tenant.onboarding_complete; canonical is tenant.status = active; both flagged for update
  - Edge cases documented: race condition (atomic CAS), all connectors inactive post-activation, abandoned onboarding (no timeout defined — gap flagged), Meta pending_review auto-trigger gap

---

## [2026-05-05] analysis | Onboarding Flow — Required Inputs (Subtask 2 of 3)

- File: wiki/analyses/onboarding-flow-inputs.md
- Question: What are the required inputs for each onboarding stage — field names, types, validation rules, sources?
- Tags: onboarding, pipeline-2, tenant-setup, connector-setup, inputs, validation, form-fields
- Sources consulted: persona-agent-spec, channel-integration-layer, execution-type-classification, meta-integration-implementation, persona-layer, orchestration-layer-spec, core-business-entities
- Notes:
  - Stage 1: 4 user fields (email, password, full_name, tos_accepted) + 1 system gate (email_verified)
  - Stage 2: 2 user fields (organization_name, organization_slug auto-generated) + system-generated tenant_id, tenant.status=onboarding, admin role
  - Stage 3: 6 user fields (business_type, industry, business_description, target_audience, geography_focus, negative_profiles); target_audience label adapts per business_type; P2-1 HYBRID step: LLM strengthens business_description before Persona Agent queued, shown for user confirmation; explicit NOT-collected table covers all 11 LLM-inferred PersonaObject/IcpDefinition fields
  - Stage 4: No form inputs; OAuth flows only; conditional page/account selection post-OAuth for Facebook (>1 page) and Instagram (>1 account); WhatsApp phone number is read-only display; Instagram uses Login path (api.instagram.com), not deprecated Facebook Login; Website connector = JS snippet external install, no UI input
  - Stage 5: No user inputs; system-only pre-flight check
  - consent_preference: not a form input; deferred to Subtask 3 (onboarding-flow-readiness)

---

## [2026-05-05] correction | Onboarding Flow — Stage Map v2 (4 issues fixed)

- File: wiki/analyses/onboarding-flow-stage-map.md
- Corrections applied after advisor review:
  1. Event gap window: webhooks activate in Stage 4 before Pipeline 1 is enabled; incoming events now captured + queued with pipeline_stage: captured; queue drained when tenant.status flips to active
  2. Pipeline 2 failure UX: resolved open question — persistent error banner on current screen, form pre-filled on return to Stage 3, re-queues from Step 1
  3. consent_preference: added to Stage 5 readiness conditions with note that user-set vs system-defaulted decision deferred to Subtask 3
  4. Field naming: standardized to tenant.status throughout (was: tenant.status:onboarding in Stage 2, tenant.onboarding_status=ready in Stage 5)

---

## [2026-05-05] analysis | Onboarding Flow — Stage Map (Subtask 1 of 3)

- File: wiki/analyses/onboarding-flow-stage-map.md
- Question: What are the onboarding stages from account creation to platform readiness?
- Tags: onboarding, pipeline-2, tenant-setup, connector-setup, readiness-check
- Sources consulted: persona-agent-spec, channel-integration-layer, orchestration-layer-spec, lead-pipeline-architecture, persona-layer, core-business-entities
- Notes:
  - 5 stages: Account Creation → Org Setup → Business Profile Input (async Pipeline 2) → Connector Setup → Readiness Check
  - Key design decision: Stage 4 (connectors) runs in parallel with async Pipeline 2 — user is never blocked waiting for LLM processing
  - Readiness Check (Stage 5) gates on two independent upstream conditions: Pipeline 2 complete AND ≥1 active channel_connection
  - Each stage documents: transition trigger, sync/async nature, failure handling, resume behavior
  - Caveats flagged: Meta App Review delay, LinkedIn allowlist delay, manual channel not yet designed, billing step not modeled
  - Placeholder references created: onboarding-flow-inputs (Subtask 2), onboarding-flow-readiness (Subtask 3)

---

## [2026-05-05] analysis | LLM Operational Safeguards

- File: wiki/analyses/llm-operational-safeguards.md
- Question: Production-ready retry, fallback, caching, token monitoring, and cost control safeguards for the LLM system
- Tags: llm, reliability, retry, fallback, caching, token-monitoring, cost-control, rating-agent, pipeline-1
- Sources consulted: rating-agent-spec, llm-io-contract, service-scaling-strategy, tech-stack-research, orchestration-layer-spec
- Four corrections applied over prior draft:
  - Rate limit retry logic: if Retry-After > 25s, skip retry entirely and return ScoringFailure(rate_limit_exhausted); do not waste retry on a call that will be rate-limited again
  - LiteLLM fallback description: re-route happens within Attempt 1 based on error response (not a proactive health check); retry counter does not increment for provider-level re-route
  - Provider pricing: must be read from a provider_pricing_config table at call time, not hardcoded; store both raw token counts and cost_usd for auditability
  - Auth failure (401/403): fires admin alert immediately — this is a production incident, not a per-lead failure
- Open gaps flagged: re-queue mechanism for rate_limit_exhausted, tokenizer library choice (tiktoken vs Anthropic SDK), provider_pricing_config entity missing from data model, anomaly threshold calibration

---

## [2026-05-05] analysis | LLM I/O Contract — Rating Agent

- File: wiki/analyses/llm-io-contract.md
- Question: Strict, machine-consumable LLM input/output JSON contracts for the Rating Agent
- Tags: rating-agent, scoring, schema, validation, json-contract, pipeline-1
- Sources consulted: rating-agent-spec, prompt-template-framework, signal-types, intelligence-layer, confidence-first-class, orchestration-layer-spec
- Design hardening applied:
  - `reasoning` promoted from freeform string to structured object (primary_driver, signal_contributors, data_gaps, salesperson_note)
  - `recommended_action` promoted from freeform string to 7-value enum (call_immediately, schedule_demo, send_pricing_deck, follow_up_scheduled, send_qualifying_message, nurture, archive)
  - Signal values typed as discriminated unions per signal class (BooleanSignal, BooleanOrPartialSignal, SpeedSignal, etc.) — eliminates false/null/not_detected ambiguity
  - `confidence` term from task resolved to `lead_completeness` per vault RESOLVED 2026-04-22
- Contracts delivered: INPUT_SCHEMA (JSON Schema draft-2020-12), OUTPUT_SCHEMA (7 LLM fields), VALIDATION_RULES (cross-field, retry, fallback, Output Schema Layer augmentation)
- Breaking changes flagged: prompt template OUTPUT FORMAT section must be updated to match structured reasoning and enum recommended_action

---

## [2026-05-04] analysis | Prompt Template Framework

- File: wiki/analyses/prompt-template-framework.md
- Question: Standard prompt template framework for all LLM interactions in the Lead Intelligence Engine
- Tags: prompt-engineering, llm, rating-agent, persona-agent, b2b, sme, scoring
- Sources consulted: orchestration-layer-spec, rating-agent-spec, persona-agent-spec, global-data-collection-architecture
- Notes: Defines four-section model (SYSTEM/CONTEXT/TASK/OUTPUT FORMAT); explains static/variable boundary for Anthropic prefix caching; documents three prompt variants (new/returning/rescore); covers all 5 LLM call types in framework coverage table; includes two full runnable samples — B2B enterprise (Rohan Mehta, CTO, TechSolve India, 120 employees, completeness 0.87, expected score 86 HOT) and SME fragmented (unknown contact, "hi interested in your product", completeness 0.52, expected score 21 COLD); clarifies which output fields the LLM writes vs which the Output Schema Layer adds post-call

---

## [2026-05-04] schema-update | Cross-wiki consistency pass — 12 documents corrected

- Trigger: comprehensive audit against global-data-collection-architecture (2026-05-03), meta-integration-implementation (2026-05-03), and tech-stack-research (2026-04-26) as ground-truth sources
- Files updated (12):

**wiki/analyses/orchestration-layer-spec.md**
  - Section 2 diagram: Pipeline 1 column redrawn — added Pre-Filter Gate, Message Parser/Haiku, Lead Ad skip note, Consent Gate, Intent Gate, await_clarification branch
  - Section 4.2 diagram: Renamed "The Six Stages" → "The Pipeline Stages"; full diagram redrawn showing two-path entry, per-lead parallel flow with Intent Gate and await_clarification branch
  - "behavioral" → "behaviour" fixed in 7 locations (dimension table, signal schema, sub_scores JSON, resolved note, Section 9 PersonaObject, Section 10 resolved row, Section 11 confirmed decision)

**wiki/analyses/execution-type-classification.md**
  - sub_scores example: `{fit:21, intent:22, engagement:17, recency:15}` → `{fit:21, intent:25, engagement:17, behaviour:12, context:9}`
  - `"model": "gpt-4o"` → `"model": "claude-sonnet-4-6"`
  - Summary table: added P1-1b (Pre-Filter Gate, AUTOMATION), P1-1c (Message Parser, AGENT), P1-3b (Intent Gate, AUTOMATION)
  - Detailed breakdown: added full specification sections for P1-1b, P1-1c, P1-3b
  - Cost attribution row: updated to reflect Sonnet (all paths) + Haiku (DM path only)

**wiki/analyses/rating-agent-spec.md**
  - Role description: "only LLM call per lead" → DM path caveat added
  - Provider: Groq/OpenAI [TBD] → RESOLVED: Anthropic Claude Sonnet 4.6 primary
  - sub_scores in Outputs section: recency removed, behaviour+context added; Soft blocker → RESOLVED 2026-05-03
  - Full ScoringOutput schema: same sub_scores fix + model field corrected
  - Per-Tenant Concurrency section: "only LLM call per lead" revised
  - Open Decisions table: LLM provider → RESOLVED; sub_scores → RESOLVED

**wiki/analyses/service-scaling-strategy.md**
  - CRITICAL: `pipeline_stage = 'scoring_failed'` → `pipeline_stage = 'human_review'` with `reason: scoring_failed`
  - "One LLM call per lead, locked" → Sonnet all paths + Haiku DM path description
  - Locked constraints table: "1 LLM call per lead" row updated
  - LLM provider Groq/OpenAI → RESOLVED to Anthropic Claude Sonnet 4.6

**wiki/analyses/delivery-integration-layer.md**
  - Added Section 3.5: Awaiting Clarification in Chat — holding section for paused leads, salesperson restriction (cannot message), card content, timeout behavior
  - CRM sync table: added `awaiting_clarification` row (not pushed, pipeline not completed)

**wiki/analyses/governance-observability-layer.md**
  - Monitoring metrics table: added "Leads in awaiting_clarification" row
  - Alert thresholds table: added "Awaiting clarification rate" row
  - `behavioral` → `behaviour` in attribution job extract block

**wiki/concepts/agent-vs-tool-classification.md**
  - Agent count: 4 → 5 (added Message Parser)
  - Pipeline 1 table: added Pre-Filter Gate, Message Parser (LLM AGENT), Intent Gate
  - Cost principle: "1 LLM call per lead" → Sonnet + Haiku description
  - Tensions section: updated "1 LLM call" language

**wiki/concepts/intelligence-layer.md**
  - sub_scores schema: recency → behaviour + context (5 fields)
  - Provider open decision: Groq/OpenAI → RESOLVED to Anthropic Claude Sonnet 4.6
  - Design principle 1: "Single LLM call per lead" → Message Parser context added
  - Open Decisions table row 1: RESOLVED

**wiki/concepts/persona-layer.md**
  - scoring_weights: `{fit, intent, engagement, recency}` → `{fit, intent, engagement, behaviour, context}`

**wiki/concepts/signal-types.md**
  - Example sub-score breakdown: `(fit=26, intent=27, engagement=18, recency=15)` → `(fit=21, intent=25, engagement=17, behaviour=12, context=9)`

**wiki/overview.md**
  - Current Thesis: "Scoring Agent is the only LLM call per lead" → DM path / Lead Ad path distinction added
  - Major Themes: agent count 4 → 5, "1 LLM call per lead" → updated
  - Open Questions item 4: "Groq vs OpenAI — open" → RESOLVED to Anthropic Claude; signal extraction note updated
  - signal detection_rule note: "preserves 1-LLM-call guarantee" → "signal extraction incurs no LLM cost"

**wiki/analyses/future-optional-agents.md**
  - "Must stay deterministic for cost control (1 LLM call per lead)" → updated with Message Parser context

---

## [2026-05-03] schema-update | orchestration-layer-spec — 6 problems fixed, 3 cross-references added

- File updated: wiki/analyses/orchestration-layer-spec.md
- Problems fixed:
  1. CRITICAL — `"model": "gpt-4o"` → `"model": "claude-sonnet-4-6"` in Scoring Agent output schema (Section 4.3)
  2. IMPORTANT — "One LLM call per lead" principle updated: Sonnet (Scoring Agent, all paths) + Haiku (Message Parser, DM path only); revised in Section 2 table footnote, Stage 2 explanation, Stage 4 intro, and Section 11 Confirmed Decisions
  3. IMPORTANT — `sub_scores` fixed: removed ghost field `recency` (no matching dimension), added `behavioral` and `context`; now five fields matching five dimensions exactly; soft-open decision in Section 10 closed as RESOLVED
  4. IMPORTANT — PersonaObject `scoring_weights` field names corrected: `{fit, intent, engagement, recency}` → `{fit, intent, engagement, behavioral, context}` (Section 9)
  5. INTERNAL CONTRADICTION — `"stage": "bucketed"` removed from Section 7.2 tool invocation envelope; `bucketed` is not a valid pipeline_stage value; enum is now `enriched | normalised | scored`
  6. IMPORTANT — `awaiting_clarification` added to pipeline_stage transitions (Section 8.1); concurrency guard (8.3) updated to skip this state explicitly; crash recovery query (8.4) updated to exclude it; pipeline_stage RESOLVED row updated in Section 9; Section 11 Confirmed Decisions entry updated
- Cross-reference gaps added:
  - Section 4.1: Two pipeline entry points (DM at Step 0, Lead Ad at Step 3) → link to global-data-collection-architecture Section 14
  - Stage 2: Consent Gate sub-step added (DPDP + GDPR check before external enrichment) → link to global-data-collection-architecture Section 10
  - Section 7.3: Enrichment API fallback chain vs orchestrator retry clarification added → links to lead-enrichment-architecture and global-data-collection-architecture Section 7
- Frontmatter: added last_updated: 2026-05-03; updated status line

---

## [2026-05-03] analysis | Meta Integration — Facebook + Instagram Connection Strategies + Pipeline Connection Point

- Files updated:
  - wiki/analyses/meta-integration-implementation.md — Added Section 1 (Facebook Page OAuth: token chain, page selection, PSID profile call, non-expiring page tokens), Section 2 (Instagram Business OAuth: Instagram Login path, 60-day token refresh job, per-app-level webhook config, IGSID User Profile API); renumbered WhatsApp to Section 3, Webhook Routing to Section 4, Lead Ads to Section 5, Checklist to Section 6; fixed SQL operator precedence bug in Section 4.4; added supersedes note for channel-integration-layer; updated checklist with 8 new items
  - wiki/analyses/global-data-collection-architecture.md — Added Section 14: two-path pipeline entry diagram (DM vs Lead Ad), NormalisedChannelEvent schema, Lead Ad pre-population field map, Instagram dual role (channel + enrichment source), Facebook PSID call at Step 9, WhatsApp identity constraints, full API call map by step with costs, Meta-to-Pipeline boundary definition
- Entities updated: none
- Concepts updated: none
- Key findings:
  - Facebook Page tokens are non-expiring; no refresh job needed
  - Instagram tokens expire in 60 days; daily refresh job mandatory; no server-side recovery after expiry
  - Instagram webhook subscribed once at App Dashboard level — no per-account API call (unlike Facebook which requires POST /{page_id}/subscribed_apps per page)
  - Two distinct Pipeline 1 entry points: DM events enter at Step 0, Lead Ad events enter at Step 3 (skip Message Parser and Signal Scorer)
  - Instagram plays dual role: channel source AND enrichment API at Step 9 (Person Resolver)
  - NormalisedChannelEvent schema defined as the contract between Meta layer and Pipeline 1
  - Supersedes: channel-integration-layer.md Instagram-via-Facebook-Page description; per-tenant webhook URL implication

---

## [2026-05-03] analysis | Global Lead Data Collection Architecture

- Wiki page: [[wiki/analyses/global-data-collection-architecture]]
- Triggered by: multi-session design conversation covering B2B/B2C classification, global enrichment, no-scraping constraint, failure modes, and production-readiness gaps
- Sources consulted: [[analyses/lead-enrichment-architecture]], [[analyses/orchestration-layer-spec]], [[analyses/signal-detection-rule-spec]], [[analyses/channel-integration-layer]], [[analyses/tech-stack-research]]
- Index updated: yes

### What is covered

- **Pre-filter gate:** noise/spam/short messages discarded before any API or LLM call
- **Message Parser (Haiku LLM):** multilingual, typo-tolerant extraction of name, company, role, location, intent, business ownership signals — solves Hinglish/non-English message failure
- **Revised LLM principle:** 1 Sonnet call per lead (Scoring Agent) + 1 Haiku call (Message Parser); no other LLM on data collection path
- **Free Signal Scorer:** deterministic B2B/B2C classification from available signals; catches micro-business owners via "I run a business" phrases
- **Jurisdiction Classifier:** libphonenumber + VAT/GST format heuristics; LLM only for ambiguous multinational cases
- **Account Graph Check:** detects multiple leads from same company; injects account-level engagement signal into Scoring Agent context
- **Conversation Thread Check:** prevents follow-up replies creating duplicate lead records; enables automated clarification re-scoring
- **Company Cache:** company_name + country_code key; 30-day TTL for registry data, 14-day for website intel
- **Company Disambiguator:** confidence threshold 80%; below threshold surfaces top matches to salesperson rather than silently picking wrong company
- **Company Resolver:** registry-driven fallback chain (Apollo → official gov API → OpenCorporates); SMB not-found handled gracefully with completeness penalty
- **Person Resolver:** staleness check (6-month window), phone cross-reference for identity_verified flag
- **Location Reconciliation:** separates lead_location from company_hq; prevents Lucknow being attributed to InMobi
- **Consent Gate:** DPDP (India) and GDPR (EU) policy check before enrichment proceeds
- **Intent Gate:** automated clarification for very_low intent + high fit leads; clarification_pending state locks salesperson manual contact
- **Global Source Registry:** India (Truecaller, MCA21, GST), UK (Companies House), US (EDGAR, OpenCorporates), EU (VIES), ME (Apollo only), SEA (ACRA, OpenCorporates)
- **Feedback Loop 2:** salesperson feedback (wrong company, stale role) invalidates cache and flags Apollo confidence — enrichment quality improves over time
- **4 real-world scenarios:** Enterprise B2B/InMobi (happy path), SMB catering business (not-found path), Hinglish message (language path), UK Barclays CTO (international path)
- **Supersedes:** India-specific provider stack in lead-enrichment-architecture (2026-04-30); signal separation principle and NormalisedEvent schema in that doc remain valid

### Key decisions from this session

- No scraping anywhere in the pipeline — all sources are official APIs or licensed commercial APIs
- Apollo.io is the global spine for B2B; Truecaller is the India B2C spine
- LLM (Haiku) used for message parsing because real messages are multilingual and typo-heavy — no regex can replace this
- Registry pattern replaces all hard-coded per-jurisdiction logic; source changes are config updates, not code deploys
- Company-level cache (not per-lead) is the primary cost optimization

---

## [2026-05-01] analysis | Meta Integration — Deep Implementation

- Wiki page: [[wiki/analyses/meta-integration-implementation]]
- Triggered by: user request to go deeper on Embedded Signup, webhook routing, and Lead Ads retrieval
- Sources consulted: [[analyses/meta-platform-api-deep-research]], [[analyses/channel-integration-layer]]
- Index updated: yes
- Cross-reference added to: [[analyses/channel-integration-layer]]

### What is covered

- WhatsApp Embedded Signup: Facebook Login for Business product setup, JS SDK `FB.login` call, popup flow, code exchange endpoint, WABA token type, phone_number_id enumeration, WABA webhook registration, signed `state` parameter for multi-tenant security, error cases
- Multi-tenant webhook routing: response-first architecture (HTTP 200 before processing), HMAC-SHA256 validation on raw bytes, `entry[].id` routing for Facebook/Instagram, `phone_number_id` routing for WhatsApp, event type dispatch inside payload, idempotent dedup via `ON CONFLICT DO NOTHING`, app-level vs page-level subscription distinction, challenge verification, stale connection monitoring
- Lead Ads retrieval: full sequence from webhook to NormalisedEvent, form definition pre-fetch via `/{page_id}/leadgen_forms`, `lead_form_field_map` table design, normalisation logic with standard + custom field handling, multi-select custom questions, `custom_disclaimer_responses`, race condition retry (code 100), polling fallback via `/{form_id}/leads`, attribution data (ad_id, adgroup_id)
- Full implementation checklist: 17 components with purpose and notes

---

## [2026-05-01] correction | Meta Platform API Deep Research — Post-Filing Accuracy Fixes

- Wiki page: [[wiki/analyses/meta-platform-api-deep-research]]
- Triggered by: advisor review identifying 2 blocking + 3 sharpening issues before filing could be considered final

### Fixes applied

**Blocking 1 — Lead retrieval time window (Section 4.3):**
- Prior text said "no documented expiry" without explanation of the 90-day figure
- Corrected to: no hard data retention expiry documented; 90-day figure in Meta docs relates to BUC rate limit calculation window, not lead deletion; best practice is fetch-immediately-and-store

**Blocking 2 — Standard Lead Form field names table (Section 3.4):**
- 14 fields (email through street_address) annotated as doc-confirmed
- 3 fields (work_email, military_status, marital_status) annotated as [training] — not confirmed in fetched documentation
- Added `GET /{form_id}?fields=questions` as authoritative source per form

**Sharpen 3 — hub.challenge response (Section 2.1):**
- Prior wording "respond with the hub.challenge integer value" was ambiguous
- Corrected to: write the challenge value as plain text HTTP response body, return HTTP 200, no JSON wrapper

**Sharpen 4 — Two-tier webhook subscription model (Section 2.1):**
- Added explicit note: app-level webhook product configuration in App Dashboard must precede per-page/per-WABA API subscription calls
- Applies to all surfaces; moved to top of Section 2 so it precedes the per-surface subscription instructions

**Sharpen 5 — Instagram token refresh trigger (Section 1.2):**
- Moved from follow-up questions into Section 1.2 body
- Documented: `expires_in` field on long-lived token response is the trigger; refresh when `expires_in` < 604800 (7 days); background job checks daily
- Removed corresponding question from Follow-up Questions section

---

## [2026-05-01] analysis | Meta Platform API Deep Research

- Wiki page: [[wiki/analyses/meta-platform-api-deep-research]]
- Triggered by: user request for comprehensive Meta API research for lead intelligence SaaS
- Sources consulted: 30+ Meta developer documentation pages via live web research
- Index updated: yes

### What is covered

**OAuth / Authorization:**
- Facebook Pages: short-lived user → long-lived user → long-lived page token (non-expiring). All permissions (pages_messaging, pages_manage_metadata, leads_retrieval, etc.) require Advanced Access + App Review + Business Verification.
- Instagram: Instagram API with Instagram Login path confirmed as current. Old `business_*` scopes deprecated January 27, 2025. New `instagram_business_*` scopes required. Long-lived Instagram User tokens valid 60 days — must refresh. No permanent token equivalent.
- WhatsApp: Embedded Signup flow → Business Integration System User token (non-expiring). One app serves multiple WABA tenants. Token type is per-tenant WABA, not per-user.

**Webhook fields + payload schemas:**
- Facebook Pages: messages, messaging_postbacks, messaging_optins, messaging_handovers, messaging_policy_enforcement, message_deliveries, message_reads, feed, leadgen — full field list documented.
- Instagram: messages, comments, live_comments, message_echoes, message_reactions, messaging_handover, messaging_optins, messaging_postbacks, messaging_referral, messaging_seen, story_insights — full JSON payloads for DM and comment events.
- WhatsApp: single `messages` field covers all inbound + status updates. Full payload schema with metadata, contacts, messages, statuses arrays documented.

**Data available per event vs follow-up calls:**
- Facebook DM: PSID in payload; name + profile_pic require follow-up GET /{psid}?fields=...
- Instagram DM: IGSID in payload; username/name/profile_pic require User Profile API call (consent-gated). Comments DO include username directly.
- WhatsApp: wa_id + profile.name in payload; profile picture/about NOT available via official Cloud API — confirmed limitation.

**Meta Lead Ads:**
- leadgen webhook delivers: leadgen_id, page_id, form_id, ad_id, created_time — no form values.
- Lead Retrieval API: GET /{leadgen_id} → field_data array with name/values. Standard field names documented.
- Permissions required: leads_retrieval, pages_manage_metadata, pages_show_list, pages_read_engagement, ads_management.

**Rate limits:**
- Page tokens: 4800 * engaged_users per 24h (BUC model)
- WhatsApp Management API: 200–5000 req/hour by account tier
- WhatsApp outbound tiers: TIER_250 → TIER_1K → TIER_10K → TIER_100K → Unlimited
- WhatsApp Cloud API max send throughput: 1000 messages/sec
- Inbound webhooks: no documented rate limit

**Multi-tenant:**
- One app, unlimited tenants confirmed.
- Routing key: page_id / IGID for Meta surfaces; phone_number_id for WhatsApp.
- System User vs Page token vs Business Integration System User — use cases distinguished.
- Token revocation: 401 error + deauthorize_callback_url; protocol documented.

### Open items resolved from channel-integration-layer

- Meta App Review requirements: RESOLVED — 2–7 days, submit 2 weeks early, all permissions listed
- WhatsApp Business Verification: RESOLVED — required for Advanced Access; ~5 days, up to 60 days
- Token lifecycle details: RESOLVED — page tokens non-expiring; Instagram 60-day refresh required; WhatsApp non-expiring

### New open items raised (added as follow-up questions in wiki page)

- Instagram token refresh job cadence
- Facebook DM profile lookup for privacy-strict users
- Instagram username Conversations API workaround vs User Profile API
- TIER_250 onboarding limitation documentation for tenants
- form_id → field name mapping table design

---

## [2026-04-30] analysis | Lead Enrichment + Investigation Architecture — Full Rewrite

- File rewritten: [[wiki/analyses/lead-enrichment-architecture]]
- File deleted: [[wiki/analyses/enrichment-provider-stack]] — merged in
- Triggered by: design conversation on lead investigation, scraper reliability, and India-specific provider stack

### What changed

**PDL on hold:** Poor coverage for Indian B2C (~20–30%) and B2B SMBs — not reliable enough for the primary pipeline.

**Two-phase enrichment model introduced:**
- Phase 1 (sync, before initial score): Tier 1 first-party + Tier 2 identity (Truecaller + Google Places)
- Phase 2 (async investigation, runs on every lead): deep social + business enrichment; score updates when complete

**India-specific investigation stack locked:**
- B2B: GST API (turnover slab — free, official), MCA API (company type/capital — free, official), JustDial (SMB profile), IndiaMART (trader/buyer status), Apollo.io (corporate employees only)
- B2C: Truecaller bio (lifestyle signals), Instagram Graph API (official), Apify Instagram (public posts only)
- Dropped: LinkedIn post scraping (too unreliable), Facebook profile scraping (mostly private, near-zero yield), WhatsApp investigation (closed system)

**Key insight:** Phone number is India's primary identity layer. Truecaller + GST + MCA give more reliable signal for Indian leads than any Western data provider. GST turnover slab directly answers B2B budget qualification.

**3 new B2B extractor types added:** gst_turnover_threshold, company_type_match, business_directory_presence (in addition to 3 existing B2C types)

**Cost model revised:** ~$180–270/mo at 300 leads/day (down from prior estimate due to free government APIs replacing paid providers)

### Open items carried forward
- 6 new extractor types not yet in signal-detection-rule-spec
- identity_graph and channel_connection entities not yet in data-entity-model
- lead_completeness formula not yet defined
- JustDial/IndiaMART: API vs scrape path not confirmed
- YouTube identity link practical path not confirmed

---

## [2026-04-28] analysis | Enrichment Provider Stack + Channel Integration Decisions

- File created: [[wiki/analyses/enrichment-provider-stack]]
- Triggered by: design conversation on exact tools, configuration, and day-1 enrichment coverage

### What was decided

**Provider stack locked:**
- Truecaller for Business — phone verification + India location coverage (~$0.001/call)
- People Data Labs (PDL) — phone/username → social handles + LinkedIn URL; pay-per-match only
- Apollo.io — LinkedIn URL → structured B2B data (job title, company, seniority)
- Instagram Graph API — IGSID/username → bio + profile (free, tenant Meta token)

**Internal identity graph as caching layer:**
- Checked before any external call; populated after every successful enrichment
- Day 1: every lead goes to external providers
- Over time: cache hit rate rises, external calls decrease
- Cannot replace external providers on day 1 — starts empty

**Why build-it-ourselves alone fails:**
- Internal identity graph starts empty; no enrichment coverage on first run
- SerpAPI search is a fallback, not a primary provider
- Real provider (PDL) needed from day 1

**Per-channel free data from webhook:**
- WhatsApp: phone + display name + message (display name avoids Truecaller name call)
- Instagram DM: IGSID → one Graph API call → username (Tier 3 enrichment starts here, free)
- Facebook DM: PSID → name only (thinnest enrichment path)
- LinkedIn Lead Ad: full profile included (skip all external calls)

**Non-text message types locked:** image (URL stored), audio (Whisper deferred), story reply (text + story ref — strong signal), product catalogue tap (product ID — highest intent signal), button click (label — strong intent)

**WhatsApp options locked:** Direct WABA (our Meta App) or BSP connector (Interakt/WATI/AiSensy) — adapter pattern, both produce identical NormalisedEvent

**Coverage expectations set:** PDL hits ~20–30% Indian B2C, ~40–55% B2B — expected behavior, not failure; low-coverage leads scored on message content + channel signals

**Cost model:** ~$270/mo at 300 leads/day; drops to ~$110/mo at 60% cache hit rate (Month 6+)

### Open items
- `identity_graph` entity not yet in data entity model — needs to be added
- Cache TTL for identity graph entries (topic_affinity especially can go stale)
- Instagram biography field availability for personal vs. creator accounts
- Whisper transcription for voice notes — deferred, flagged for post-MVP

---

## [2026-04-28] analysis | Lead Enrichment Architecture + Channel Integration Layer

- Files created: [[wiki/analyses/lead-enrichment-architecture]], [[wiki/analyses/channel-integration-layer]]
- Triggered by: design discussion on how enrichment works, how tenants connect platforms, and how Tier 3 social enrichment improves B2C scoring accuracy

### What was decided

**Signal separation principle (non-negotiable architectural rule):**
- Signals are created ONLY from ICP + tenant persona in Pipeline 2 — no lead data involved
- Enrichment is independently collected in Pipeline 1 — no signal awareness
- Signal evaluation is the bridge: detection_rules run against NormalisedEvent to produce 0.0–1.0 values
- These three steps are always distinct and must never be conflated

**Three-tier enrichment model:**
- Tier 1: first-party interaction data (message content, website behavior, lead history) — always available, $0
- Tier 2: identity resolution + firmographic (Truecaller for phone verify, Clay/PDL for social handle discovery, Apollo/Clearbit for B2B firmographic) — ~$0.005–$0.02/lead
- Tier 3: social behavioral enrichment (Instagram Graph API for public profile + posts, Apollo for LinkedIn topics) — ~$0.02–$0.10/lead, requires Tier 2 to have found a social handle

**Tier 3 step-by-step from name + phone:**
1. Truecaller → verified name, city, spam check
2. Clay/PDL identity graph → Instagram handle / LinkedIn URL (if indexed)
3a. Instagram Graph API → bio, recent post hashtags → topic_affinity inferred
3b. Apollo → LinkedIn job + posting topics
- Realistic Tier 3 success rate from WhatsApp: 15–25% (private accounts and no Meta phone registration = no Tier 3)

**Source channel affects enrichment difficulty:**
- Instagram DM / Facebook DM → social user ID in event payload → Tier 3 requires no lookup
- LinkedIn Lead Ad → full profile in form response → richest inbound source
- WhatsApp → phone only → all 3 steps required

**NormalisedEvent field expansion:** 6 new fields for Tier 2 identity handles + Tier 3 social behavioral data

**New extractor types required for B2C:** `topic_affinity_match`, `interest_category_match`, `bio_keyword_match` — must be added to signal-detection-rule-spec and Persona Agent Step 3 prompt

**New entity required:** `channel_connection` — not yet in data entity catalog; covers OAuth tokens, webhook endpoints, connection status per platform per tenant

**enrichment_tier_reached field** needed on `lead_enrichment` entity

### Files created
- [[wiki/analyses/lead-enrichment-architecture]] — enrichment tiers, Tier 3 flow, signal separation, NormalisedEvent expansion, new extractor types, B2C vs B2B strategy
- [[wiki/analyses/channel-integration-layer]] — OAuth flow per platform, channel_connection entity, webhook + polling event detection, payload normalisation adapters, token lifecycle

### Follow-up items flagged
- Add `channel_connection` to [[concepts/data-entity-model]] Group A
- Add `enrichment_tier_reached` field to `lead_enrichment` entity definition
- Add 3 new B2C extractor types to [[analyses/signal-detection-rule-spec]] and update Persona Agent Step 3 system prompt
- Confirm Clay.com vs PDL as primary Tier 2/3 provider
- Confirm Instagram Graph API scope for public post reading

---

## [2026-04-28] analysis | Signal Detection Rule — Format Specification

- File created: [[wiki/analyses/signal-detection-rule-spec]]
- Triggered by: design discussion on event trigger → lead enrichment flow; detection_rule was the last hard blocker
- Status: RESOLVES hard blocker flagged in 8 documents across the wiki

### What was decided
- **Format:** `{ type, source_fields, params }` — named extractor + params
- **Vocabulary:** 13 pre-built extractor types covering all 5 scoring dimensions (keyword_match, question_pattern, urgency_indicator, budget_authority_indicator, touchpoint_count, channel_diversity, recency_check, page_visit_match, form_completion_depth, source_type_match, utm_match, geography_match, company_attribute_match)
- **Output contract:** every extractor returns `(detected: bool, value: float 0.0–1.0, evidence: str)` — uniform across all types
- **No composition:** one extractor per signal; AND/OR logic is not supported; composition is handled by multiple signals across dimensions
- **Persona Agent change:** Step 3 now emits detection_rule JSON directly (not a placeholder). No engineering mapping step. Vocabulary table given in Step 3 system prompt.
- **Stateful extractors noted:** touchpoint_count, channel_diversity, recency_check require lead_history from DB — enrichment is not purely stateless
- **NormalisedEvent schema defined:** minimal schema all event sources normalize into before Pipeline 1 runs

### Files updated (blocker resolved in all)
- [[wiki/analyses/persona-agent-spec]] — Step 3 logic + output schema + open decisions
- [[wiki/analyses/orchestration-layer-spec]] — signal schema section + enrichment step + two open decisions table entries
- [[wiki/analyses/execution-type-classification]] — Open Question 3 + Follow-up 3
- [[wiki/analyses/tech-stack-research]] — Open Items #1 + Follow-up #5
- [[wiki/analyses/service-scaling-strategy]] — Caveats section
- [[wiki/concepts/data-entity-model]] — Open Questions (signal schema)
- [[wiki/overview]] — Open Question #1, What's TBD, What to Read Next, #12
- [[index]] — new analysis entry added

---

## [2026-04-26] analysis | Technology Stack Research — Complete Production Stack

- File created: [[wiki/analyses/tech-stack-research]]
- Triggered by: team request to research all tools for production microservices build
- Context established: AWS confirmed, EC2 account available, web chat on product site, signal detection_rule still TBD, senior dev decision = Microservices (not Monolithic)

### Locked decisions (no further discussion needed)
- Backend: Python 3.12 + FastAPI + Uvicorn + uv
- LLM: Anthropic Claude Sonnet 4.6 (primary) + OpenAI GPT-4o (fallback) via LiteLLM
- Containers: AWS ECS Fargate
- Auth: Clerk (native multi-tenancy, free tier, 4-role RBAC)
- Secrets: AWS Secrets Manager
- Observability: CloudWatch (MVP) → Grafana Cloud + Prometheus (Month 3+)
- Package manager: uv
- Ruled out: Laravel/PHP (no LLM ecosystem), Go (SDK friction), EKS (overkill), Lambda (15-min timeout), Datadog (cost), Auth0 (cost), Groq (no prompt caching), Vault (overkill), CockroachDB (overkill), Neon/Supabase (not AWS-native)

### Three open decisions (pending team discussion)
1. **Orchestration:** Temporal self-hosted on EC2 (~$30/mo, native crash recovery) vs AWS Step Functions (~$0.05/mo, no mid-task resumption) — full landscape of 14 tools researched; Celery/Airflow/Prefect/Dagster all ruled out
2. **Real-time chat:** Pusher + Beams (~$49/mo, zero ops) vs Soketi on EC2 + FCM (~$35/mo, Pusher-compatible, same code) — full landscape of 13 tools researched
3. **Database:** Aurora Serverless v2 (~$94/mo, zero ops, auto-scale) vs PostgreSQL on EC2 (~$42/mo, team owns ops) — full landscape of 10 options researched

### Budget scenarios documented
- Scenario A (Managed): ~$357/month excl. LLM tokens
- Scenario B (Hybrid self-hosted): ~$288/month excl. LLM tokens
- LLM cost (steady state with prompt caching): ~$27/month for 300 leads/day

---

## [2026-04-26] analysis | Agent Specifications — Persona Agent, Rating Agent, Future Optional Agents

- Files created: [[wiki/analyses/persona-agent-spec]], [[wiki/analyses/rating-agent-spec]], [[wiki/analyses/future-optional-agents]]
- Sources consulted: [[concepts/agent-vs-tool-classification]], [[concepts/intelligence-layer]], [[concepts/persona-layer]], [[concepts/signal-types]], [[analyses/orchestration-layer-spec]], [[analyses/execution-type-classification]], [[analyses/delivery-integration-layer]], [[analyses/scoring-quality-metrics]], [[concepts/confidence-first-class]]

### Persona Agent (persona-agent-spec.md)
- Defined as the Pipeline 2 configuration agent — 3 sequential LLM sub-agents (Business Persona → ICP → Signal Definitions)
- Inputs: tenant business description (from P2-1 intake), optional re-run context (feedback pattern, check-in change description), team_lead_approval required for re-runs
- Outputs: PersonaObject (scoring_weights, banding, custom_rules, tone), IcpDefinition (target_segment, priority_signals, disqualifying_signals, buying_triggers), signal[] (all 5 dimensions), prompt template (orchestrator generates post-Step-3, AUTOMATION)
- Named distinction from Persona Engine (TOOL that loads/caches at scoring time) explicitly documented
- Invocation: new tenant onboarding OR feedback-driven re-run OR check-in-driven re-run; never per-lead; never automatic
- Step 3 output constrained: weights_within_dim must sum to 1.0 per dimension

### Rating Agent (rating-agent-spec.md)
- Defined as the full score_lead() call — encompasses 4 internal components (Persona Engine, Prompt Layer, Rating Agent component, Output Schema Layer)
- Inputs: EnrichedLead, tenant_id, variant (new/returning/rescore), signal_values dict, prompt_template_version
- Score output: score (int 0-100), bucket (enforced by banding), sub_scores (per dimension)
- Reasoning output: reasoning (one-line), recommended_action (simple string — deliberately limited at MVP)
- Completeness output: lead_completeness (float 0.0-1.0) + needs_review (bool) — **NOT LLM confidence** (2026-04-22 correction maintained)
- Per-tenant concurrency cap: recommend 2 per tenant (not global) — prevents noisy neighbor
- Timeouts: 30s LLM call, 60s full score_lead(), 90s orchestrator budget
- Soft blocker noted: sub_scores has 4 fields in S2 spec vs 5 scoring dimensions — S2 to clarify

### Future Optional Agents (future-optional-agents.md)
- **Recommendation Agent:** fills gap between "what to do" and "how to approach this specific lead"; outputs personalized outreach draft, talking points, channel recommendation, timing window; unlock conditions: 3+ months data, AP1/AR2/AR3 stable, CRM outcomes connected; introduce as A/B opt-in for one tenant first
- **Workflow Agent:** adds judgment to lifecycle decisions (vs deterministic SLA/decay rules); outputs decision (rescore/escalate/hold_decay/archive), rationale, approval proposal; unlock conditions: 3+ months stability, AR1 baseline, tenant workflow patterns documented; introduce with narrow scope (re-score triggers only) first
- Both agents defined as enhancements, not corrections — MVP delivers full core value without them
- Defined what should NOT become an agent (deduplication, signal extraction, bucket enforcement, quality metrics)
- Principles for future agent expansion: data prerequisite, determinism, cost proportionality, oversight, minimal set tests

---

## [2026-04-26] analysis | Execution Type Classification — Automation / Agent / Hybrid

- Wiki page: [[wiki/analyses/execution-type-classification]]
- Question: Which steps in the Lead Intelligence Engine workflow are automation, agent-driven, or hybrid?
- Sources consulted: [[concepts/agent-vs-tool-classification]], [[analyses/orchestration-layer-spec]], [[concepts/intelligence-layer]], [[concepts/lead-pipeline-architecture]], [[analyses/governance-observability-layer]]

### Classification summary

- **AGENT (3 steps):** Onboarding Agent (P2-2), ICP Agent (P2-3), Signal Agent (P2-4) — all in Pipeline 2, all one-time per tenant
- **HYBRID (3 steps):** Tenant Info Intake (P2-1) — form scaffold + LLM strengthening of inputs; Scoring (P1-5) — Rating Agent LLM call + Output Schema Layer banding enforcement; Proactive Check-In (G-10) — conditional on classifier type (TBD)
- **AUTOMATION:** All remaining steps — Data Gather, Lead Enrichment (both phases), Normalise, Prompt Fill, Disqualification Gate, Bucketize, routing, delivery, all lineage/governance/background jobs

### Key architectural findings

- The hybrid boundary at Scoring (P1-5) is defined by the Output Schema Layer enforcing banding rules that can override the LLM's bucket — within the same atomic `score_lead()` call. This is not a separate validation step.
- Signal extraction (P1-2b) is AUTOMATION despite using signal definitions created by an LLM Agent (P2-4). Intelligence is front-loaded into signal design; execution is deterministic per-lead.
- The 1-LLM-call-per-lead guarantee holds: the only per-lead LLM cost is in the HYBRID Scoring step (Rating Agent component).
- Three open questions can shift G-9, G-10 classifications: check-in classifier type, recommendation wording approach, detection_rule format.

### Design implications documented

- Test strategy per execution type (unit tests for AUTOMATION, eval suites for AGENT, both for HYBRID)
- Debugging approach: check signal extraction values first, then LLM judgment
- Cost attribution: LLM costs incurred only in AGENT and HYBRID steps
- Observability signal scope per execution type

---

## [2026-04-26] schema-update | Flag deleted analyses — success-metrics-framework and success-metrics-brief

- Files affected: index.md
- success-metrics-framework.md: marked DELETED in index; file was removed from filesystem; log entries from 2026-04-14 and 2026-04-16/17 preserved; content superseded by scoring-quality-metrics combined doc
- success-metrics-brief.md: marked DELETED in index; file was removed from filesystem; log entries from 2026-04-17 preserved

---

## [2026-04-24] analysis | Service Scaling Strategy — Three MVP Services

- Question: What are the best ways to scale the Ingestion, Orchestration+LLM, and Reporting services?
- Wiki page: [[wiki/analyses/service-scaling-strategy]]
- Reference: Tod Golding, *Building Multi-Tenant SaaS Architecture* (O'Reilly)
- Sources consulted: orchestration-layer-spec, delivery-integration-layer, governance-observability-layer, concepts/intelligence-layer, concepts/lead-pipeline-architecture, scoring-quality-metrics

### Key findings

- **Isolation model:** Pool for all three services at MVP. ~300 leads/day across 3 tenants does not justify silo infrastructure. Bridge model is the long-term commercial direction.
- **#1 architectural win:** Change Scoring Agent concurrency cap from global (5) to per-tenant (2 per tenant). Current global cap allows one tenant's batch to starve all others — textbook noisy neighbor. Per-tenant semaphore keyed on tenant_id fixes this in ~20 lines of code.
- **Ingestion:** Job queue absorbs spikes; every job stamped with tenant_id at intake; per-tenant rate limits per channel connector; lineage writes are non-negotiable (must not be batched or delayed); idempotent enrichment required before retry logic added.
- **Orchestration+LLM:** Per-tenant concurrency cap; per-tenant LLM config stored in tenant record; system message used for prompt caching; 60s hard timeout enforced; crash recovery via pipeline_stage already locked in design.
- **Reporting:** quality_snapshots is the enforced read model — no dashboard query touches raw pipeline tables; read replica connection string separated from day one; RBAC enforced server-side in API layer; scheduled reports pre-computed by background job; per-tenant LLM cost metering logged at call time.
- **Tiering framework:** Basic/Standard/Premium config schema designed now, activated later. Per-tenant config fields for concurrency cap, token budget, API rate limit, report schedule.
- **Five changes that move the needle now:** (1) per-tenant concurrency cap, (2) per-tenant config schema with limit fields, (3) tenant_id stamped at queue intake, (4) quality_snapshots rule enforced, (5) LLM token usage logged per tenant per call.

### Constraints verified

- All 15 recommendations cross-checked against locked design decisions. No conflicts with: 1 LLM call per lead, governance failure must not halt pipelines, delivery failures never roll back Pipeline 1, system proposes / human approves, lineage write-order rule, pipeline_stage crash safety guarantee, RLS + JWT + RBAC.

---

## [2026-04-22] schema-update | Cross-document propagation — Delivery and Integration Layer

- Trigger: delivery-integration-layer.md created; all other docs updated to reference it and reflect its position in the system architecture

### Files updated

**wiki/analyses/orchestration-layer-spec.md**
- Section 2 (main architecture diagram): "Bucketize → salesperson" → "Bucketize"; added DELIVERY AND INTEGRATION LAYER box between Pipeline 1 output and GOVERNANCE LAYER; shows feedback signal flow back to governance
- Section 4.2 (Pipeline 1 stage flow): Bucketize bottom replaced with DELIVERY AND INTEGRATION LAYER box instead of "Salesperson sees ranked lead cards in chat"
- Section 4.2 (Bucketize box): "confidence routing" corrected to "completeness routing"
- Section 6.3 step 10: updated to reference Delivery Layer handoff and [[analyses/delivery-integration-layer]]

**wiki/analyses/governance-observability-layer.md**
- Section 1 (position diagram): redesigned to show Pipeline 1 output first going to Delivery Layer, then feedback signals flowing from Delivery Layer to Governance Layer
- Section 2.3 (alert delivery): added reference to [[analyses/delivery-integration-layer]] Section 4 (notification_delivery entity, channel decisions)
- Section 5.5 (team lead notification delivery): added reference to [[analyses/delivery-integration-layer]] Section 4

**wiki/overview.md**
- Current Thesis: added paragraph on Delivery Layer (what it covers, delivery failures never roll back Pipeline 1, full spec reference)
- Major Themes: added delivery-integration-layer analysis entry
- Key Analyses table: added delivery-integration-layer.md as COMPLETE 2026-04-22; fixed confidence-scoring-brainstorm from "IN PROGRESS" → "RESOLVED 2026-04-22"; corrected orchestration-layer-dependencies to SUPERSEDED

**wiki/concepts/data-entity-model.md**
- Related Concepts: added [[analyses/delivery-integration-layer]] entry for Group C delivery entities

**wiki/concepts/lead-pipeline-architecture.md**
- Pipeline diagram: added DELIVERY AND INTEGRATION LAYER between Bucketize and GOVERNANCE LAYER with feedback signal flow
- Pipeline 1 stage table: Scoring Agent output corrected (confidence → lead_completeness, needs_review)
- Lead Status Transitions: "confidence < 50%" → "lead_completeness below threshold"
- Quality metrics table: "Confidence value" → "lead_completeness value"
- Related Concepts: added [[analyses/delivery-integration-layer]] entry

---

## [2026-04-22] analysis | Delivery and Integration Layer

- File created: [[wiki/analyses/delivery-integration-layer.md]]
- Covers: chat interface (primary delivery surface), notifications, dashboards, CRM sync, external API + webhooks, report delivery
- Sources consulted: [[sources/2026-lead-intelligence-engine-reference]], [[sources/2026-intelligence-layer-design]], [[sources/2026-core-business-entities]]
- Related analyses: [[analyses/orchestration-layer-spec]] (handoff point — delivery begins when pipeline_stage = 'delivered'), [[analyses/governance-observability-layer]] (feedback loop and notification_delivery entity)

### Key decisions documented

- Chat is the primary delivery surface — lead cards, HOT alerts, SLA breach alerts, team lead recommendations, and proactive check-ins all delivered in chat
- HOT leads get immediate push notification; WARM/COLD get ranked list delivery only
- Four S1 delivery entities confirmed: `dashboard_definition`, `notification_delivery`, `delivery_endpoint`, `report_definition`
- `delivery_endpoint` is the config record for every external integration (CRM, webhook) — scoped by tenant_id, credentials via vault reference
- CRM push: HOT and WARM pushed immediately; COLD timing TBD; human_review and failed leads not pushed
- Webhook payload signed with HMAC-SHA256; endpoints must use HTTPS
- Delivery failures do not roll back Pipeline 1 — score and lineage are already persisted
- RBAC-scoped access across every surface (admin · team_lead · salesperson · viewer)
- Report cadences: weekly (team lead) + monthly (team lead + product owner) — content pulled from quality_snapshots

### Open decisions recorded
- Alert delivery channel for SLA breaches and recommendations (chat / email / both) — TBD
- Dashboard tooling (in-product vs external BI) — TBD
- Report format (PDF / HTML / inline chat) — TBD
- CRM sync for COLD bucket (immediate vs daily batch) — TBD
- Bidirectional CRM sync for outcome data — recommended for Month 2+
- Full list: Section 12 of the analysis doc

- Index updated with new analysis entry

---

## [2026-04-22] schema-update | Closing stale analyses — confidence-scoring-brainstorm and orchestration-layer-dependencies

- Files updated: wiki/analyses/confidence-scoring-brainstorm.md, wiki/analyses/orchestration-layer-dependencies.md
- confidence-scoring-brainstorm: status changed IN PROGRESS → RESOLVED. Resolution section added at top. Final answer: no confidence score, only `lead_completeness` (float 0.0–1.0). Brainstorm history preserved. One open item remains: threshold value for needs_review.
- orchestration-layer-dependencies: rewritten with resolution status per blocker. All S1/S2 items resolved except `signal.detection_rule` format. Old terminology (Agent E, Phase 00–06, pipeline_log, `confidence` field) mapped to current names. Confirmed as superseded by orchestration-layer-spec.

---

## [2026-04-22] schema-update | Completing orchestration-layer-spec and governance-observability-layer with S1 + S2 deliverables

- Files updated: wiki/analyses/orchestration-layer-spec.md, wiki/analyses/governance-observability-layer.md
- Based on: [[sources/2026-intelligence-layer-design]] (S2) + [[sources/2026-core-business-entities]] (S1)

### orchestration-layer-spec.md — what was completed

1. **Scoring Agent output schema** — locked by S2. Replaced placeholder JSON with the actual ScoringOutput fields: `score` (int), `bucket` (lowercase), `reasoning` (one-line string), `lead_completeness` (float 0.0–1.0), `sub_scores` (object), `recommended_action`, `needs_review` (bool), `schema_version`, `prompt_version`, `model`. Full field-by-field explanation added.
2. **ICP Agent schema** — updated to show ICP feeds into PersonaObject.icp; stored as `ideal_customer_profile` entity by S1; versioned via `ideal_customer_profile_version`. TBD removed.
3. **Signal entities** — updated to confirm `signal` and `signal_evaluation` are formal S1 entities. `detection_rule` format still the one remaining open item.
4. **Lead completeness routing** — replaced "Confidence routing" with "Lead completeness routing". Explained what needs_review means, how the Output Schema Layer sets it, and what "human review queue" actually is (filtered view of leads, not a separate table).
5. **pipeline_stage values** — locked. S1 implements exactly: captured → fetched → enriched → normalised → scored → delivered / human_review / failed.
6. **pipeline_log → three-entity model** — replaced single-table description with pipeline_run + task_execution + lineage_record. Field tables added for each. `confidence` → `lead_completeness` in lineage fields.
7. **Section 9 hard blockers** — all resolved except `detection_rule` format. Resolved: pipeline_stage values, data store entities, Scoring Agent schema, PersonaObject, ICP, signal entities, human_review_queue.
8. **Section 10 open decisions** — marked resolved items, added lead completeness threshold and sub_scores field count as new open items.
9. **Section 11 confirmed decisions** — added 8 new confirmed decisions from S1/S2.

### governance-observability-layer.md — what was completed

1. **"confidence distribution" monitoring metric** — updated to "lead completeness distribution" throughout. Clarified it measures enrichment completeness, not LLM certainty.
2. **pipeline_log schema** — replaced single-table TBD with the three-entity model: pipeline_run, task_execution, lineage_record. Each entity explained in plain English with its specific question it answers.
3. **Lineage section** — updated to name the three entities; explained how audit and lineage relate in the new model.
4. **attributed_feedback table** — updated: `dimension_scores JSONB` → `sub_scores JSONB`; `explanation_reasons TEXT[]` → `reasoning TEXT`; `confidence INTEGER` → `lead_completeness NUMERIC(4,3)`. Field notes added explaining each change.
5. **Pattern detection** — `confidence` band → `lead_completeness` band; example output updated.
6. **Section 8 tables map** — expanded to include full S1 entity list referenced throughout the doc.
7. **Section 9 open questions** — resolved items marked; `leads.assigned_to` remains the one unresolved S1 item; added lead completeness threshold as new TBD.
8. **Section 10 confirmed decisions** — added 10 new confirmed decisions from S1/S2.

### One remaining open item
`signal.detection_rule` format — S2's design document explicitly lists this as an unresolved decision. Lead Enrichment stage code cannot be written until this is locked. Everything else is unblocked.

---

## [2026-04-22] ingest | Intelligence Layer Design + Core Business Entity Catalog

- Files: raw/assets/intelligence_layer_design.docx + raw/assets/core_business_entity.docx
- Wiki pages (sources): [[wiki/sources/2026-intelligence-layer-design]], [[wiki/sources/2026-core-business-entities]]
- Concepts created: [[wiki/concepts/intelligence-layer]], [[wiki/concepts/signal-types]], [[wiki/concepts/data-entity-model]]
- Concepts updated: [[wiki/concepts/persona-layer]] (added Persona Engine details, data model backing, versioning confirmation), [[wiki/concepts/confidence-first-class]] (major correction — see below)
- Overview, index, and log updated
- **Key correction applied:** The intelligence layer design doc uses the term "confidence" for an LLM output field. The user confirmed this is **not a confidence score** — it is a **lead completeness score**. The `needs_review` routing logic and the 3-band threshold gate are unchanged, but the input is lead data completeness rather than LLM self-assessed certainty. This correction propagates through: `confidence-first-class` concept (status updated, calculation section rewritten), `intelligence-layer` concept (ScoringOutput schema field renamed to `lead_completeness`), `overview.md` (correction noted in What's Changed), and both new source pages.
- Notes: Documents are related — intelligence_layer_design.docx defines the layer that produces `lead_score`; core_business_entity.docx defines the entity that stores it. Cross-references wired throughout. Signal entity schema (detection_rule format) remains a hard blocker; noted in both the data entity concept page and the updated open questions list.

---

## [2026-04-19] schema-update | Full Documentation Audit — Governance Structure, Orchestration KPI Integration, Diagrams

- Files updated: wiki/analyses/governance-observability-layer.md, wiki/analyses/orchestration-layer-spec.md
- Supporting updates: wiki/overview.md, index.md, wiki/concepts/lead-pipeline-architecture.md

### governance-observability-layer.md — 3 structural defects fixed

1. **Duplicate Section 5** — Feedback Loops and Quality Tracking were both numbered Section 5. Fixed: Feedback Loops = Section 5, Quality Tracking = Section 6. Section 1 table already had the correct numbering; the body now matches it.
2. **Wrong subsection numbering inside Quality Tracking** — sub-sections read `6.2`, `6.3`, `6.4` while parent heading was Section 5. Fixed: parent renamed to Section 6; subsection `5.1 Approach` renamed to `6.1 Approach`; `6.2/6.3/6.4` were already correct after parent rename.
3. **Wrong section ordering** — Feedback Loops was buried after Security Controls (Section 7) and New Tables (Section 8). Fixed: Feedback Loops moved to Section 5, directly after Lineage (Section 4). Dependency order is now: Monitoring → Auditability → Lineage → Feedback Loops → Quality Tracking → Security.

### governance-observability-layer.md — how/why reasoning added throughout all 6 domains

- **Section 1:** Why governance is a separate layer (not in pipeline critical path); why the 6 domains are ordered the way they are (dependency chain — each section can reference the one before it)
- **Section 2:** Why each monitoring metric exists; why alert thresholds are not set before Month 1 baseline
- **Section 3:** Why two audit surfaces not one — `pipeline_log` (what system did) vs `access_log` (what user did) answer fundamentally different questions; mixing makes both unqueryable
- **Section 4:** Why lineage must be built before the second LLM agent (retrofit cost grows as ~n² due to interlocking concurrent state, not n×); why one table serves both lineage and audit purposes
- **Section 5:** Why feedback loops exist (system degrades silently without them); why 3-step not 1-step (raw thumbs down is useless without attribution; attribution without pattern detection produces overreaction); why attribution fires immediately not weekly; why weekly fixed-count threshold not daily rate-based; why 5 team lead action options; why the loop is slow by design
- **Section 6:** Why SQL jobs against existing tables (no new infrastructure = no new sync problem); why 3 cadences not 1 (per-run answers operational health, weekly answers salesperson behaviour, monthly answers business value — different time horizons); why thresholds set after Month 1
- **Section 7:** Why 3 security layers (each defends different failure mode: code bugs / identity spoofing / privilege misuse); why 4 RBAC roles not 2 or 10; why PII encrypted but scores are not; why credentials in vault not DB; why soft deletes during normal operation

### orchestration-layer-spec.md — 4 KPI cross-reference gaps closed

1. **Quality tracking row (Section 5 table)** — added `[[analyses/scoring-quality-metrics]]` link
2. **Global KPIs paragraph (Section 5)** — added paragraph naming all 3 Global KPIs, who reviews each, at what cadence, and what a drop in System Health means operationally
3. **Confidence routing (Stage 5 Bucketize)** — added "Why this threshold" column to routing table; added paragraph connecting the 3 confidence bands to the per-run confidence distribution KPI and its alert trigger
4. **Lineage writes (Section 8.5)** — added paragraph stating lineage is the data foundation for all quality metrics; added field-by-field table mapping each lineage field to the specific quality metrics that depend on it

### orchestration-layer-spec.md — 2 new diagrams added

1. **Section 2 System Architecture (updated)** — governance box expanded to show: lineage write arrows from both pipelines; Quality Tracking sub-layer with 3 cadence columns (PER-RUN / WEEKLY / MONTHLY); quality_snapshots merge point; 3 Global KPI outputs (System Health, Business Health, Tenant Health Rate); team lead review note and config-back-to-orchestrator arrow
2. **Section 5.1 Quality Metrics Orchestration Flow (new)** — full lifecycle diagram from pipeline run end → per-lead lineage in pipeline_log → 3 SQL job cadences → quality_snapshots → Global KPIs (with WHO and WHEN annotated per KPI) → team lead + product owner review → two recalibration paths (bucket threshold via AP1/AP2; feedback-driven via weight/prompt/ICP re-run) → back to ORCHESTRATOR with specific config fields updated. Includes "How to read" table and rationale for why the loop is intentionally slow.

### Concepts explained in session (not previously documented)

- **Scoring Agent concurrency cap (recommend: 5)** — why a cap exists (rate limits + cost control); how the queue works (5 always running, next enters as one finishes); why 5 is the starting recommendation
- **Timeout threshold for concurrency guard (recommend: 15–30 min)** — what problem it solves (distinguishing active processing from crashed run); why too short causes unnecessary retries; why too long causes recovery delay; why 15-30 min sits safely above any realistic healthy stage duration

---

## [2026-04-19] schema-update | Orchestration Layer Spec — Final Document Rewrite

- File rewritten: wiki/analyses/orchestration-layer-spec.md
- Purpose: full rewrite into plain English, readable in one go, with proper diagrams
- Diagrams added: system architecture (orchestrator + two pipelines + governance), Pipeline 1 fan-out (6-stage with parallel lead processing), fill-in-the-blanks prompt mechanism (before/after signal slot filling)
- All three S3 pillars fully documented: Controller, Tool Invocation, State Tracking
- All confirmed decisions, open decisions, and S1/S2 hard + soft blockers retained
- Removed: redundant internal explanations, excessive sub-headers, verbose normalisation rule lists
- Structure: 11 sections — What it is → Architecture → Pipeline 2 → Pipeline 1 → Governance → Controller → Tool Invocation → State Tracking → S1/S2 contracts → Open decisions → Confirmed decisions
- Status remains: COMPLETE

---

## [2026-04-19] schema-update | Orchestration Layer Spec — COMPLETE

- File updated: wiki/analyses/orchestration-layer-spec.md
- Status: IN PROGRESS → COMPLETE (tool invocation envelope proposed; pending S1/S2 confirmation)
- Section 5.1 fixed: "3-role RBAC" → "4-role RBAC (admin, team_lead, salesperson, viewer)"
- Section 5.1 fixed: Feedback loops row updated from `[TBD]` to reference governance-observability-layer Section 5
- Index updated: orchestration-layer-spec status updated to COMPLETE

**Full document coverage (Subtask 3 — S3):**
- Section 1: Purpose & Scope
- Section 2: Architecture Overview — two pipelines, 4 LLM agents
- Section 3: Pipeline 2 (Onboarding — Onboarding Agent, ICP Agent, Signal Agent)
- Section 4: Pipeline 1 (Event/Lead — Data Gather, Lead Enrichment, Normalise, Scoring Agent, Bucketize)
- Section 5: Governance Layer (cross-cutting — reference to full governance doc)
- Section 6: Orchestration Controller Responsibilities (Pipeline 2 + Pipeline 1 orchestration, cross-pipeline coordination)
- Section 7: Tool Invocation (capability registry, standard envelope, retry policies)
- Section 8: State Tracking (stage transitions, stage update rule, concurrency guard, lineage writes, run-level state, crash recovery)
- Section 9: Interface Contracts Needed (hard + soft blockers for S1/S2)
- Section 10: Open Questions
- Section 11: Confirmed Decisions

---

## [2026-04-19] schema-update | Governance Layer — Proactive Tenant Check-In + Open Questions Fix

- File updated: wiki/analyses/governance-observability-layer.md
- Section 5.7 added: Proactive Tenant Business Check-In
  - Scheduled check-in via existing chat interface (cadence TBD: 2-week or monthly range)
  - Recipient: team_lead of the tenant (TBD — confirm with team)
  - Response handling: 4-step flow — natural language response → Intent Classifier → no change / minor update / significant change
  - Significant change → ICP + Signal Agent re-run (Pipeline 2) with team lead approval
  - Check-in event logged to access_log
  - Rule: system suggests, human approves. Never automatic. [LOCKED principle]
  - Connection to Add-on 8 (deferred): check-in is proactive schedule-driven; Add-on 8 is data-pattern-driven — both use same chat surface and same principle
- Pipeline 2 re-run triggers in orchestration-layer-spec.md updated to document both mechanisms (check-in + feedback-driven)
- Open Questions section fixed: mislabeled "## 6. Quality Tracking" renamed to "## 9. Open Questions"
- 4 new TBDs added to Open Questions: check-in cadence, check-in recipient, message wording, flagging threshold (N)
- Confirmed Decisions updated:
  - "3 roles" → "4 roles: admin, team_lead, salesperson, viewer"
  - Added: team_lead tenant-scoped decision
  - Added: proactive check-in confirmed decisions (3 rows)

---

## [2026-04-19] schema-update | Governance Layer — Feedback Loop + 4-Role RBAC

- File updated: wiki/analyses/governance-observability-layer.md
- Status updated: IN PROGRESS → COMPLETE
- Feedback loop fully documented (Section 5):
  - 3-step enforcement loop: attribution (immediate) → pattern detection (weekly) → team lead action
  - Attribution extracts from lineage: signal_version, prompt_version, fired_signals, dimension_scores, explanation_reasons, confidence
  - New table: attributed_feedback (enriched feedback with lineage data)
  - Pattern detection: groups by signal_version, prompt_version, fired_signals, explanation_reasons
  - Flagging threshold: [TBD — fixed count approach confirmed]
  - Action on pattern: re-run ICP + Signal Agent (not full Pipeline 2, not Signal only)
  - Other actions: adjust weight manually, update prompt template, investigate, dismiss
  - System suggests, human approves — never automated [LOCKED]
  - Recommendations sent to: Team Lead role (tenant-scoped)
- RBAC updated: 3 roles → 4 roles
  - Added: team_lead (tenant-side, scoped to own tenant; receives enforcement recommendations)
  - Existing: admin, salesperson, viewer
  - user_roles CHECK constraint updated
- Duplicate security section removed; section numbering corrected

---

## [2026-04-19] analysis | Governance and Observability Layer

- Wiki page: [[wiki/analyses/governance-observability-layer]]
- Domains documented: monitoring, auditability, lineage, quality tracking, security controls
- Feedback loops: deferred to next discussion
- Key decisions:
  - Quality tracking: scheduled SQL jobs against existing Postgres tables; 3 cadences (per-run, weekly, monthly); results to `quality_snapshots` table; no new infrastructure
  - Alert thresholds: `[TBD — after Month 1 baseline]`
  - Security — 3-layer model:
    - Layer 1: Postgres RLS on every tenant-scoped table (enforced at DB level)
    - Layer 2: JWT with tenant_id + role claims (1h expiry + refresh)
    - Layer 3: 3-role RBAC (admin, salesperson, viewer)
  - Credentials: secrets vault (AWS Secrets Manager or HashiCorp — TBD); never in DB or code
  - PII: encrypted at rest (phone, email, name, address)
  - Audit: pipeline_log (transformations) + access_log (user actions) — two surfaces
  - Soft deletes only during normal operation; hard deletes only during archival
  - Retention policy: `[TBD — per jurisdiction]`
- New tables added: `access_log`, `quality_snapshots`, `user_roles`
- Governance layer failure must not halt Pipeline 1 or Pipeline 2

---

## [2026-04-19] schema-update | Architecture Revision — Two-Pipeline Model + Playbook Integration

- Files updated: wiki/analyses/orchestration-layer-spec.md, wiki/concepts/lead-pipeline-architecture.md, wiki/concepts/agent-vs-tool-classification.md, wiki/overview.md
- Source added: raw/assets/lead_intelligence_manual_enrichment_playbook (1).docx (referenced, not formally ingested)
- Key changes from original single-pipeline architecture:
  - Two pipelines confirmed: Pipeline 2 (Onboarding — one-time per tenant), Pipeline 1 (Event/Lead — per lead)
  - LLM agent count: 1 → 4 (Onboarding Agent, ICP Agent, Signal Agent in Pipeline 2; Scoring Agent in Pipeline 1)
  - Per-lead LLM cost preserved: still 1 LLM call per lead (Scoring Agent only)
  - Signal extraction is deterministic (TOOL), not LLM — separation of extraction vs scoring
  - Prompt mechanism: fill-in-the-blanks template; Signal Agent creates slots, Lead Enrichment fills values
  - Bucket thresholds updated: 75/45 → 80/55/0 (playbook values; tenant-configurable starting points)
  - Pipeline 1 stage order confirmed: event → data gather → lead enrichment → normalise → scoring → bucketize
  - Governance Layer added as explicit cross-cutting layer (monitoring, auditability, lineage, feedback, quality, security)
  - 10 enrichment dimensions documented from playbook (digital footprint, social/web, company intelligence, transactional behavior, intent signals, behavioral sequence, geo/context, psychographic proxy, network/referrals, external triggers)
- New open questions surfaced: signal detection_rule format, Pipeline 2 re-run triggers, 4-agent LLM cost estimate

---

## [2026-04-19] analysis | Orchestration Layer — Responsibilities Specification (IN PROGRESS)

- Wiki page: [[wiki/analyses/orchestration-layer-spec]]
- Deliverable: Subtask 3 — Orchestration Controller, Tool Invocation, State Tracking
- Audience: S1 (data layer) and S2 (intelligence layer) developers
- Confirmed design decisions:
  - Run model: mixed-mode (batch at Agent A, per-lead fan-out for B→C→D→E, single-threaded aggregation at Phase 06)
  - Cross-lead parallelism: included from v2.0 (not deferred); concurrency cap on Agent E [TBD recommend 5]; shared rate limiter across fan-out
  - Concurrency guard: status-based (not DB locks); non-terminal + recent = skip; non-terminal + stale = resume; timeout_threshold [TBD recommend 15-30 min]
  - Stage update rule: pipeline_stage is the final atomic write after lineage + output_data written
  - Lineage writer: orchestrator (not tools); written after every tool call, every phase
  - Crash recovery: resume from current pipeline_stage; 2-retry budget per stage; Agent E re-invocation accepted tradeoff
  - Background jobs (decay, SLA tracker, feedback collector): NOT in orchestrator primary flow
  - Agent E retry policy: 2-attempt with per-failure-mode handling; route to human_review_queue on exhaustion
  - Capability registry: resolved once at Phase 00; zero orchestrator changes per new use case
- Proposed (needs S1/S2 confirmation): tool invocation standard envelope (input/output shape)
- Hard blockers still open: pipeline_stage values (S1), pipeline_log schema (S1), Agent E output JSON schema incl. confidence field (S2)
- Status: IN PROGRESS — crash recovery and tool envelope pending final discussion confirmation

---

## [2026-04-17] analysis | Orchestration Layer — Dependency Analysis

- Wiki page: [[wiki/analyses/orchestration-layer-dependencies]]
- Question: What must S1 (data layer) and S2 (intelligence layer) devs complete before subtask 3 (orchestration layer) can be defined?
- Context: Story = Define System Layer; user is assigned subtask 3
- Hard blockers identified (3): `leads` pipeline_stage field values, `pipeline_log` schema, Agent E output schema (especially confidence field format)
- Soft blockers (4): tenant_config fields, persona object structure, Agent D output format, Agent E failure modes
- Key finding: orchestrator sits between both layers and cannot be designed without knowing the interface contracts on both sides

---

## [2026-04-17] analysis | Scoring Quality Metrics — Global KPIs Section Added

- File updated: wiki/analyses/scoring-quality-metrics.md
- Added Global KPIs section at end of document
- 3 global KPIs: System Health (Pipeline Coverage + Score Stability), Business Health (Scoring Lift + HOT Response Rate), Tenant Health Rate (composite, blocked until Month 1 baseline)
- Written for non-technical readers — plain language, no jargon
- Pairs kept separate within each KPI to prevent hidden failures from averaging

---

## [2026-04-17] schema-update | Scoring Quality Metrics — Universal Formula Rewrite

- File updated: wiki/analyses/scoring-quality-metrics.md
- All formulas rewritten using plain descriptive names — no Greek symbols, no subscript notation, no set operators
- Formulas now self-explanatory at first glance for any audience
- Variable sections retained for data source context
- Metrics without a single formula retain their explanation of why plus a plain-language calculation method

---

## [2026-04-17] schema-update | Scoring Quality Metrics — Mathematical Formula Pass

- File updated: wiki/analyses/scoring-quality-metrics.md
- All formulas rewritten in mathematical notation with named variables
- Every variable explained with its data source
- Metrics without a single formula: AP2 Part 1 (relational check), AP3 (completeness formula pending count vs weight decision), C3 (blocked on TBD thresholds — skeleton formula provided), C5 (deterministic engineering check — no statistical formula appropriate), AR3 (distribution — formula given per-lead, then three aggregates), AR4 (breakdown — per-type formula given, no pass/fail formula), AR5 (session definition pending team decision)
- One open decision surfaced: AP3 completeness formula needs count-based vs weight-based decision from team

---

## [2026-04-17] schema-update | Accuracy Proxy — AP2 + AP3 Combined

- Files updated: wiki/analyses/scoring-quality-metrics.md, wiki/analyses/accuracy-proxy-metrics.md
- Change: AP2 (Monotonicity Check, diagnostic) and AP3 (Discrimination Ratio, primary) merged into single primary metric AP2 (Bucket Separation)
- AP3 slot reassigned to Completeness Qualifier (previously AP4)
- Reason: both metrics used same BOR values and were always read together; separating them was artificial

---

## [2026-04-17] analysis | Scoring Quality Metrics — Combined Document

- Wiki page: [[wiki/analyses/scoring-quality-metrics]]
- Contains: Score Coverage Rate (new) + Accuracy Proxy + Consistency + Action Relevance
- Each section is self-contained; nothing moved between groups
- Score Coverage Rate added as prerequisite health check before the three sub-stories
- Individual group files (accuracy-proxy-metrics.md, consistency-metrics.md, action-relevance-metrics.md) retained separately

---

## [2026-04-17] analysis | Action Relevance — Metric Group Card

- Wiki page: [[wiki/analyses/action-relevance-metrics]]
- Part of story: Define scoring quality metrics → sub-story: action relevance
- Primary metrics: AR1 SLA Compliance Rate, AR2 Action Rate by Bucket
- Diagnostic checks: AR3 Time-to-Action Distribution, AR4 Action Type Distribution by Bucket, AR5 Salesperson Priority Alignment
- Open decision: WARM SLA cutoff needs to be locked (48h or 72h) before AR1 can be calculated
- Targets: TBD — product owner and team leads to set after Month 1 data
- Notes: All three scoring quality sub-stories now complete

---

## [2026-04-17] analysis | Consistency — Metric Group Card

- Wiki page: [[wiki/analyses/consistency-metrics]]
- Part of story: Define scoring quality metrics → sub-story: consistency
- Primary metrics: C1 Cross-Run Bucket Stability, C2 Temporal Score Drift
- Diagnostic checks: C3 Boundary Flip Rate (blocked on TBD thresholds), C4 Decay-Rescore Coherence, C5 Signal Contribution Consistency (engineering check)
- Targets: TBD after Month 1 baseline
- Notes: C3 shares the same bucket threshold blocker as confidence-scoring-brainstorm; C5 should be a unit test at build time

---

## [2026-04-17] analysis | Accuracy Proxy — Metric Group Card

- Wiki page: [[wiki/analyses/accuracy-proxy-metrics]]
- Part of story: Define scoring quality metrics → sub-story: accuracy proxy
- Structure: metric group card (no individual KPI cards); primary metrics + diagnostic checks
- Primary metrics: AP1 Bucket Outcome Rate (per bucket), AP3 Discrimination Ratio (BOR_HOT / BOR_COLD)
- Diagnostic checks: AP2 Monotonicity (pass/fail), AP4 Completeness Qualifier (pass/fail)
- Positive outcome definition: any one of — responded, meeting booked, qualified, deal closed, thumbs up; treated equally
- Targets: TBD after Month 1 baseline
- Notes: success-metrics-framework.md and success-metrics-brief.md found deleted from filesystem; noted in index

---

## [2026-04-17] analysis | Success Metrics Brief — Stakeholder Version Created

- Wiki page: [[wiki/analyses/success-metrics-brief]]
- Trigger: User request — full framework is too long to present to a boss; condensed version needed
- Action: New file created; existing framework untouched
- Same 12 metrics, same 4 dimensions, same 2 hard targets
- Each metric reduced to 2-4 sentences: why it exists, what the calculation does, where any number comes from
- Links back to [[analyses/success-metrics-framework]] for full detail

---

## [2026-04-17] analysis | Success Metrics Framework — v3 Full Explanatory Rewrite

- Wiki page: [[wiki/analyses/success-metrics-framework]]
- Trigger: User review — previous versions listed metrics without explaining why each exists or how calculations work
- Action: Full rewrite in plain English; every metric explains its WHY, every calculation explains its basis, every threshold explains where it comes from and why that number
- Structure retained: 4 dimensions (Scoring Quality, Accuracy Proxy, Consistency, Action Relevance), 12 metrics, 2 hard targets (CO1 ≥90%, CO2 ≤5pt)
- Key explanations added: ground truth problem (why accuracy is measured via proxies), why bucket boundaries are guesses not data-derived, why 5pt is the CO2 limit, why feedback is tracked per bucket not overall, why decay-rescore coherence matters, why SLA windows are tenant-capacity-dependent
- Blockers still documented: bucket score boundaries (most urgent), human review SLA window, CRM data source, feedback loop go-live

---

## [2026-04-17] analysis | Confidence Scoring Brainstorm

- Wiki page: [[wiki/analyses/confidence-scoring-brainstorm]]
- Status: IN PROGRESS — user not yet clear, discussion to resume
- What was established:
  - Signals + weights are per-tenant, per-persona (dev team configures)
  - Three types of uncertainty exist: data, signal contradiction, boundary proximity
  - Enrichment-based confidence (weighted signal coverage) is circular — ruled out
  - Boundary proximity is the only thing confidence can add that enrichment score doesn't
- What changed: confidence-first-class.md marked UNDER REVIEW; previous 2026-04-16 decision on calculation method reopened
- Blocker: bucket thresholds (HOT/WARM/COLD score boundaries) are TBD — confidence formula cannot be finalised without them
- Next step: define bucket boundaries, then resume confidence discussion

---

## [2026-04-16] schema-update | Confidence Calculation + Metrics Framework Revised

**Change 1 — confidence-first-class.md**
- Resolved TBD: confidence is derived from enrichment score threshold, not LLM self-reported
- Reasoning: LLMs are poorly calibrated at self-reporting certainty; deterministic calculation is more reliable
- Routing logic unchanged; only the calculation method is now decided

**Change 2 — success-metrics-framework.md**
- Replaced over-engineered v1 (25+ metrics, assumption-based targets, statistical formulas) with lean v2
- 12 metrics across 4 dimensions, split by when data is actually available
- No targets set upfront except 2 hard operational ones (CO1 prompt coverage, CO2 cross-run stability)
- Removed: ECE, KL divergence, shadow re-runs, 4-tier hierarchy, 25-scenario edge case catalogue
- Added: guiding principle — measure first, set targets after Month 1 baseline
- Index: updated

---

## [2026-04-14] analysis | Success Metrics Framework
- Wiki page: [[wiki/analyses/success-metrics-framework]]
- Question: Define measurable product KPIs — scoring quality, accuracy proxy, consistency, action relevance
- Structure: 4-tier hierarchy (North Star → Health Scorecard → Diagnostic → Infrastructure), 4 dimensions + Meta, 25 catalogued edge cases, 8 open decisions
- Tier 0 candidates: A2 (HOT:COLD Conversion Ratio ≥2.5×), D5 (Per-Salesperson Lift ≥+20% median)
- Top decision recommendation: adopt Curiosity Budget (5% COLD leads called weekly) and capture pre-launch baseline — both structurally unrecoverable if skipped
- Index: updated (1 analysis added)

---

## [2026-04-14] ingest | Multi-Tenant Adaptive Lead Intelligence Engine — Master Reference
- File: raw/assets/lead_intelligence_engine_reference.md
- Wiki page: [[wiki/sources/2026-lead-intelligence-engine-reference]]
- Entities created: gamoft, urvee-organics, govmen, anishekh (4 new)
- Concepts created: lead-pipeline-architecture, agent-vs-tool-classification, persona-layer, confidence-first-class, lineage-log, disqualification-gate, score-decay, action-sla, capability-registry, feedback-loop, adaptive-signal-lifecycle (11 new)
- Overview: updated with domain, thesis, themes, open questions
- Index: updated (1 source, 4 entities, 11 concepts)
- Notes: First source. Domain is Lead Intelligence Engine POC for Gamoft. ~50 TBDs open across technology stack, tenant personas, DB schemas, and algorithm decisions. Adaptive Signal Lifecycle (Add-ons 6/7/8) explicitly deferred to Sprint 2-3.

---

## [2026-04-14] session-start | Initial Setup
- Schema: CLAUDE.md created
- Structure: wiki/, wiki/sources/, wiki/entities/, wiki/concepts/, wiki/analyses/, raw/, raw/assets/ created
- Index: index.md initialized (0 sources)
- Notes: Fresh vault. Awaiting domain selection and first source ingest.
