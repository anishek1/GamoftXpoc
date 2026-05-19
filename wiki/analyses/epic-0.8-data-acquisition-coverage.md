---
type: analysis
question: "Epic 0.8 JIRA stories reference a 'scraping workflow' — does the system cover these requirements, and how should JIRA be updated to match what was actually designed?"
date: 2026-05-19
tags: [jira, epic-0.8, enrichment, no-scraping, data-acquisition, coverage-mapping, devops]
sources_consulted:
  - "[[analyses/lead-enrichment-architecture]]"
  - "[[analyses/enrichment-tools-integration]]"
  - "[[analyses/global-data-collection-architecture]]"
  - "[[analyses/devops-controls]]"
  - "[[analyses/b2c-data-acquisition]]"
  - "[[analyses/signal-detection-rule-spec]]"
status: COMPLETE
---

# Epic 0.8 — Data Acquisition Coverage & JIRA Rename

**Question:** Epic 0.8 JIRA stories reference a "scraping workflow" — does the system cover these requirements, and how should JIRA be updated to match what was actually designed?
**Date:** 2026-05-19

---

## Plain-English Summary

**The mismatch:** JIRA Epic 0.8 is titled "Data Acquisition & Scraping Workflow Design" with stories about scraping inputs, outputs, and merge logic. The Lead Intelligence Engine has a hard **no-scraping policy**: it uses only official government APIs (MCA21, GST Portal, Companies House), licensed commercial APIs (Apollo.io, Tracxn, Probe42), and managed gateway services (Surepass). No website is scraped.

**The resolution:** Every requirement buried in the "scraping" stories is fully covered — just by a different mechanism (API-first enrichment). The content exists. The JIRA story titles and descriptions need to be renamed to reflect the actual design. This document maps every story and sub-task to its wiki coverage and specifies the exact rename for each.

---

## The No-Scraping Decision

**Decision:** The system never scrapes websites. All external data is sourced via official APIs, licensed commercial APIs, or managed gateway services.

**Why:**
1. **Legal risk** — India's DPDP Act 2023, UK GDPR, and platform Terms of Service (LinkedIn, Instagram, Facebook) prohibit unauthorized scraping of personal and company data. A scraping violation exposes all three POC tenants to legal liability.
2. **Data reliability** — scraped data has no schema guarantee, breaks on HTML changes, and is not the source of record. Official APIs return structured, versioned data.
3. **Maintenance cost** — scrapers require continuous maintenance as website layouts change. API integrations are stable.
4. **Tenant trust** — clients using the platform to process their own leads must trust that data acquisition is compliant. Scraping undermines this trust.

**Where this decision is documented:**
- [[analyses/lead-enrichment-architecture]] §1 (signal-separation principle, no-scraping stated)
- [[analyses/global-data-collection-architecture]] §2 (explicit statement: "The system uses only official government APIs... It does not scrape any website.")
- [[analyses/b2c-data-acquisition]] (B2C data acquisition: 4-method hierarchy, API-first, no-scraping hard policy)

---

## Story-by-Story Coverage Map

### Story 1 — "Define data source strategy"
**JIRA description:** Identify and classify all data sources needed for enrichment.

**Status: ✅ Fully covered.**

| JIRA sub-task | Covered by | Where |
|---|---|---|
| List internal sources | CRM history, past orders, platform events, intake log | [[analyses/lead-enrichment-architecture]] §3; [[analyses/orchestration-layer-spec]] §4.3 Stage 2 |
| List external sources | Full global source registry: Apollo, Truecaller, MCA21, GST Portal, Companies House, Surepass, Probe42, Tracxn, NewsCatcherAPI, Serper, OpenCorporates, PDL | [[analyses/global-data-collection-architecture]] §4–5 (The Global Source Map); [[analyses/enrichment-tools-integration]] |
| Classify source reliability | Per-provider confidence, staleness rules, tier classification (T1/T2/T3), jurisdiction availability | [[analyses/lead-enrichment-architecture]] §enrichment tiers; [[analyses/enrichment-tools-integration]] §WHY per tool |

**JIRA rename:** No rename needed — this story title is accurate. ✅

---

### Story 2 — "Define scraping workflow"
**JIRA description:** Design how company information is fetched and converted into structured enrichment data.

**Status: ✅ Fully covered — but entirely via API, not scraping.**

This story's intent — "how do we get company data and turn it into structured enrichment data?" — is answered in detail. The mechanism is the **Source Registry + Company Resolver**, not scraping.

| JIRA sub-task | What it maps to in the API-first design | Covered by |
|---|---|---|
| Define scraping inputs | Enrichment trigger inputs: `company_name + country_code` (B2B), `phone_number` (B2C India), `linkedin_url` (B2B LinkedIn) | [[analyses/global-data-collection-architecture]] §7 (Step 7 Company Disambiguator inputs); [[analyses/enrichment-tools-integration]] §WHERE per tool |
| Define scraping outputs | `NormalisedCompanyProfile` schema: industry, size, founded year, revenue estimate, directors, GST status, registry verification status | [[analyses/global-data-collection-architecture]] §8 (Step 8 Company Resolver outputs); [[analyses/lead-enrichment-architecture]] §NormalisedEvent field expansion |
| Define merge logic | Source Registry fallback chain: Apollo → Surepass/MCA21/Companies House → OpenCorporates; most recent API data wins; CRM data overrides self-reported; conflict flagged for human review | [[analyses/global-data-collection-architecture]] §8 (Company Resolver, "tried in order"); [[analyses/orchestration-layer-spec]] §4.3 Stage 3 (normalise, conflict resolution) |

**JIRA rename required:**

| Current title | Rename to |
|---|---|
| "Define scraping workflow" | "Define enrichment workflow" |
| "Define scraping inputs" | "Define enrichment API trigger inputs" |
| "Define scraping outputs" | "Define NormalisedCompanyProfile output schema" |
| "Define merge logic" | "Define enrichment fallback chain and data merge rules" |

**Story description update:**
> ~~Design how company information is fetched and converted into structured enrichment data via scraping.~~
> Design how company information is fetched via the Source Registry API chain and converted into a NormalisedCompanyProfile. The Source Registry pattern means data sources are defined in config — adding a new country or provider requires no code change.

---

### Story 3 — "Define scraping DevOps controls"
**JIRA description:** Plan rate limits, scheduling, and operational safeguards for scraping flows.

**Status: ✅ Fully covered in [[analyses/devops-controls]] §Epic 0.8.**

This story maps directly to the enrichment DevOps controls already documented.

| JIRA sub-task | What it maps to | Covered by |
|---|---|---|
| Define scheduler strategy | Enrichment is per-lead (triggered by Pipeline 1, not batched); 8 background jobs on cron schedule | [[analyses/devops-controls]] §0.8.1 |
| Define throttling and rate limits | `enrichment_quota` table; 90% threshold triggers skip + next provider in fallback chain; cost-cap per provider | [[analyses/devops-controls]] §0.8.2 |
| Define scrape failure logging | Per-call `enrichment_source_failed` structured log events; daily enrichment health snapshot to `quality_snapshots`; alert if provider success rate < 50% | [[analyses/devops-controls]] §0.8.3; [[analyses/observability-detail-spec]] §1.3 |

**JIRA rename required:**

| Current title | Rename to |
|---|---|
| "Define scraping DevOps controls" | "Define enrichment DevOps controls" |
| "Define scheduler strategy" | "Define enrichment scheduler and background job strategy" |
| "Define throttling and rate limits" | "Define enrichment provider rate limit and quota management" |
| "Define scrape failure logging" | "Define enrichment failure logging and health monitoring" |

**Story description update:**
> ~~Plan rate limits, scheduling, and operational safeguards for scraping flows.~~
> Plan rate limits, scheduling, and operational safeguards for the API-based enrichment workflow. Covers the per-lead trigger model, the `enrichment_quota` table for rate limit tracking, the daily health snapshot background job, and alert thresholds per provider.

---

## Summary: What JIRA Epic 0.8 Should Look Like

**Epic title rename:**
> ~~0.8 Data Acquisition & Scraping Workflow Design~~
> **0.8 Data Acquisition & Enrichment Workflow Design**

**Epic description update:**
> ~~Design data acquisition strategy for internal data, external APIs, and scraping-based enrichment workflows.~~
> **Design the API-first data acquisition strategy for enrichment: internal data sources, the global Source Registry of external APIs, the Company Resolver pipeline, the NormalisedCompanyProfile output schema, the enrichment fallback chain, and the operational controls (rate limiting, scheduler, failure logging).** Scraping is explicitly out of scope — all external data is sourced via official government APIs, licensed commercial APIs, or managed gateway services.

**Full rename table:**

| Current JIRA title | Rename to | Coverage |
|---|---|---|
| 0.8 Data Acquisition & Scraping Workflow Design | 0.8 Data Acquisition & Enrichment Workflow Design | — |
| Define data source strategy | Define data source strategy *(no change)* | ✅ |
| List internal sources | List internal sources *(no change)* | ✅ |
| List external sources | List external sources *(no change)* | ✅ |
| Classify source reliability | Classify source reliability *(no change)* | ✅ |
| Define scraping workflow | Define enrichment workflow | ✅ |
| Define scraping inputs | Define enrichment API trigger inputs | ✅ |
| Define scraping outputs | Define NormalisedCompanyProfile output schema | ✅ |
| Define merge logic | Define enrichment fallback chain and data merge rules | ✅ |
| Define scraping DevOps controls | Define enrichment DevOps controls | ✅ |
| Define scheduler strategy | Define enrichment scheduler and background job strategy | ✅ |
| Define throttling and rate limits | Define enrichment provider rate limit and quota management | ✅ |
| Define scrape failure logging | Define enrichment failure logging and health monitoring | ✅ |

---

## Evidence

- No-scraping policy (source: [[analyses/global-data-collection-architecture]] §Introduction)
- Source Registry pattern and Company Resolver chain (source: [[analyses/global-data-collection-architecture]] §7–8)
- NormalisedCompanyProfile and NormalisedEvent field expansion (source: [[analyses/lead-enrichment-architecture]] §NormalisedEvent; [[analyses/enrichment-tools-integration]])
- Enrichment scheduler, throttling, failure logging (source: [[analyses/devops-controls]] §0.8.1–0.8.3)
- B2C data acquisition hierarchy (source: [[analyses/b2c-data-acquisition]] §Method hierarchy)

## Caveats & Gaps

- **Surepass, Probe42, Serper credentials pending** — architecture is locked but endpoint credentials are not yet obtained. This does not block JIRA rename.
- **"Merge logic" for B2C leads** — the merge rules for person-level (not company-level) data are described in [[analyses/global-data-collection-architecture]] §Step 9 but not consolidated into a single spec. If a formal B2C enrichment merge spec is needed, file a separate story.

## Follow-up Questions

- Who owns updating the JIRA story titles? (Recommend: Anishekh as project owner, before Sprint 1 planning)
- Should the Epic 0.8 description also note that the no-scraping policy is a **hard non-goal** (same weight as "no raw PII to viewer role")? Currently it is documented in the analysis docs but not listed in the Epic's acceptance criteria.
