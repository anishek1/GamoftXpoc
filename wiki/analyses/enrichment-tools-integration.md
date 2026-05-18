---
type: analysis
question: "How do Surepass, Probe42, Tracxn, NewsCatcherAPI, and Serper integrate into the Lead Intelligence Engine enrichment pipeline — why, how, where, and when is each tool used?"
date: 2026-05-16
tags: [enrichment, surepass, probe42, tracxn, newscatcher, serper, pipeline-1, source-registry, normalised-event, b2b, india, global, lead-enrichment]
sources_consulted:
  - "[[analyses/lead-enrichment-architecture]]"
  - "[[analyses/global-data-collection-architecture]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/signal-detection-rule-spec]]"
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/inngest-function-design]]"
  - "[[concepts/lead-pipeline-architecture]]"
status: COMPLETE — endpoint credentials pending for Surepass, Probe42, Serper; architecture fully locked
---

# Enrichment Tools Integration — Surepass, Probe42, Tracxn, NewsCatcherAPI, Serper

**Question:** How do these five tools integrate into the Lead Intelligence Engine enrichment pipeline?
**Date:** 2026-05-16

---

## Plain-English Summary

The existing enrichment stack (Apollo, Truecaller, GST Portal, MCA21, Instagram Graph API) handles the majority of lead enrichment. Five new tools are being added to close specific gaps that the current stack cannot address:

- **Surepass** replaces unreliable direct government API calls with a single managed gateway and adds new verification types not currently supported
- **Probe42** provides Indian SMB financial intelligence — balance sheets, court records, Probe Score — that neither Apollo nor government APIs carry
- **Tracxn** adds startup and growth-company intelligence: funding stage, last round amount, investors — the only source for this data
- **NewsCatcherAPI** fills a complete gap — no source currently captures company news signals, which are a strong leading indicator of budget availability and buying intent
- **Serper** acts as the last-resort fallback when every structured API returns nothing, preventing zero-enrichment leads from entering scoring with no data

All five tools fit into the existing Source Registry pattern — config-driven, no hard-coded logic, no redeployment required to add or remove a source.

---

## Tool 1 — Surepass

### WHY

The current stack calls the GST Portal API and MCA21 API directly as government endpoints. Both have the same problem: they are free, official, and correct — but they are also unreliable. No SLAs, no uptime guarantees, frequent downtime during peak hours, and no structured error handling. When either goes down, the enrichment step silently fails and the lead scores with missing business data.

Surepass is a managed API gateway that wraps 240+ Indian government verification sources under one endpoint, one API key, one authentication token, and one SLA. It also unlocks new verification types the current stack does not have at all: PAN to Company lookup (finds company CIN and GST from just a PAN number), Bank Account Verification, Udyam/MSME registration, and TAN verification.

**The core reason:** One managed dependency with uptime guarantees is better than two raw government endpoints with none — and Surepass adds capabilities on top that are not otherwise available.

### WHAT IT PROVIDES

| API | What It Verifies | What It Returns | Current Stack Equivalent |
|---|---|---|---|
| GST Verification API | GSTIN number | Business name, status (Active/Cancelled/Suspended), registration date, business nature, state jurisdiction, taxpayer type | GST Portal API (direct) — replaces |
| MCA CIN API | Company CIN number | Company name, type (Pvt Ltd/LLP/OPC), status, incorporation date, registered address, authorized capital, paid-up capital, directors | MCA21 API (direct) — replaces |
| MCA DIN API | Director DIN number | Director name, status, DOB, associated companies | MCA21 API (direct) — replaces |
| MCA Filed Documents Pull API | Company CIN | Filed MCA documents (annual returns, balance sheets) | Not in current stack — new |
| PAN to Company API | PAN number | Company CIN, GSTIN list, director details, financial standing | Not in current stack — new |
| TAN Verification API | TAN number | TAN status, deductor name | Not in current stack — new |
| Udyam Aadhaar API | Udyam number | MSME registration status, enterprise category (Micro/Small/Medium), NIC code | Not in current stack — new |
| Bank Account Verification API | Account number + IFSC | Account holder name, bank name, account status | Not in current stack — new |
| FSSAI Verification API | FSSAI license number | Food business legitimacy, license validity | Not in current stack — new |

### WHERE — Pipeline Step

**Tier 2 (synchronous) and Phase 2 (async), Step 8 — Company Resolver**

Surepass runs in two phases depending on which API is called:

```
Tier 2 (synchronous — runs before initial score):
  → GST Verification API      (always, for B2B India leads with GSTIN)
  → MCA CIN API               (always, for B2B India leads with CIN)

Phase 2 (async — runs after initial score):
  → PAN to Company API        (fallback: GSTIN unknown, PAN available)
  → MCA Filed Documents API   (for larger companies where financial depth matters)
  → Udyam API                 (when lead message mentions MSME or small business)
  → Bank Account Verification (post-MVP: payment risk assessment)
```

### WHEN — Trigger Conditions

```
GST Verification:
  TRIGGER when: country_code = "IN" AND enriched_business_flag = true
                AND (GSTIN captured from message OR found via Apollo)

MCA CIN Verification:
  TRIGGER when: country_code = "IN" AND enriched_business_flag = true
                AND (CIN captured OR Apollo returned company name → search MCA by name)

PAN to Company:
  TRIGGER when: GST Verification returned null (GSTIN not found)
                AND PAN number available in message or form fields

Udyam Verification:
  TRIGGER when: message contains "MSME" OR "small business" OR "udyam"
                OR company_size (from Apollo) < 50

Bank Account Verification:
  TRIGGER when: Phase 2+ only — after lead is scored HOT
                (verify payment details before committing sales resources)
```

### HOW — API Integration

**Base URL:** `https://kyc-api.surepass.io/api/v1`
**Auth:** `Authorization: Bearer {SUREPASS_TOKEN}`
**Method:** POST on all endpoints
**Format:** JSON request body, JSON response

**GST Verification call:**
```http
POST https://kyc-api.surepass.io/api/v1/corporate/gstin
Authorization: Bearer {SUREPASS_TOKEN}
Content-Type: application/json

{ "id": "27AADCB2230M1ZV" }
```

**MCA CIN call:**
```http
POST https://kyc-api.surepass.io/api/v1/corporate/cin
Authorization: Bearer {SUREPASS_TOKEN}
Content-Type: application/json

{ "id": "U72200KA2007PTC043198" }
```

**PAN to Company call:**
```http
POST https://kyc-api.surepass.io/api/v1/corporate/pan-to-company-details
Authorization: Bearer {SUREPASS_TOKEN}
Content-Type: application/json

{ "id": "AADCB2230M" }
```

Note: Exact endpoint paths above are architecture-design. Final paths confirmed after API key onboarding with Surepass support.

### NormalisedEvent Fields Populated

```python
# Replaces what was coming from direct GST + MCA21 calls
enriched_gst_registered: bool
enriched_gst_status: str              # "Active" | "Cancelled" | "Suspended"
enriched_gst_turnover_slab: str       # "1Cr–5Cr" — from GST Portal data
enriched_business_nature: list[str]   # ["Wholesale Business", "Retail Business"]
enriched_company_type: str            # "pvt_ltd" | "llp" | "opc" | "sole_proprietor"
enriched_paid_up_capital: int         # INR
enriched_incorporation_date: str      # ISO date
enriched_registered_address: str      # full registered address
enriched_directors: list[str]         # director names

# New — not available from direct govt APIs
enriched_pan_verified: bool
enriched_msme_registered: bool
enriched_msme_category: str | None    # "Micro" | "Small" | "Medium"
enriched_tan_verified: bool | None
```

### Source Registry Position

```yaml
IN:
  B2B:
    - source: apollo              # Step 1: company overview, person
    - source: surepass_gstin      # Step 2: replaces GST Portal API (sync)
    - source: surepass_cin        # Step 3: replaces MCA21 API (sync)
    - source: surepass_pan        # Step 4: fallback if GSTIN unknown (async)
    - source: probe42             # Step 5: financial depth
    - source: tracxn              # Step 6: startup intelligence
    - source: newscatcher         # Step 7: news signals
    - source: justdial            # Step 8: SMB directory
    - source: indiamart           # Step 9: B2B trading presence
    - source: serper              # Step 10: last-resort fallback
```

### Cost and Timing

| Call | Phase | Timing | Approx Cost |
|---|---|---|---|
| GST Verification | Tier 2 | Sync — before initial score | Contact Surepass |
| MCA CIN | Tier 2 | Sync — before initial score | Contact Surepass |
| PAN to Company | Phase 2 | Async — after initial score | Contact Surepass |
| Filed Documents | Phase 2 | Async — after initial score | Contact Surepass |

**Company Cache TTL:** 30 days — government data changes slowly.

---

## Tool 2 — Probe42

### WHY

Apollo.io is the global spine for company enrichment. It covers large enterprises and funded startups well. But for Indian SMBs — a catering business in Lucknow, a textile trader in Surat, a packaging manufacturer in Pune — Apollo returns nothing or a single line with no financial data. These leads cannot be scored accurately because the system has no verified data about their business size, financial health, or legitimacy.

Probe42 specifically indexes Indian companies from 700+ public sources including MCA, GST, EPFO, court databases, and credit bureaus. It covers 21 million active Indian companies. More importantly, it provides data that no other source in the stack carries: balance sheets, P&L statements, EBITDA, net worth, court/legal cases, ROC charge filings, and a proprietary Probe Score (1–5 financial health rating). These fields directly answer the most important B2B qualification question: does this company have the financial capacity to buy?

**The core reason:** Apollo tells you WHO a company is. Probe42 tells you WHETHER they can afford to buy.

### WHAT IT PROVIDES

| Data Category | Fields | Signal Value |
|---|---|---|
| Company Identity | CIN, company name, registered address, incorporation date, status | Confirms company exists and is active |
| Directors & Ownership | Director names, DIN numbers, beneficial owner | Verifies decision-maker identity |
| Financial Statements | Balance sheet, P&L, revenue, EBITDA, net worth, debt-to-equity | Direct budget signal |
| ROC Filings | Annual return dates, charge filings, compliance status | Business health signal |
| Legal Records | Court cases (count and status), legal disputes | Risk signal |
| Credit Intelligence | Probe Score (1–5), credit ratings, financial stability | Composite creditworthiness |
| GST Compliance | GST filing regularity, return status | Operational health signal |
| EPFO Data | Employee provident fund records | Actual employee count proxy |

### WHERE — Pipeline Step

**Phase 2 (async), Step 8 — Company Resolver, after Apollo**

Probe42 always runs for Indian B2B leads. Even when Apollo returns good data, Probe42 adds financial depth that Apollo does not carry. The two sources are complementary, not competitive.

```
Step 8 Company Resolver — India B2B path:

  Apollo call → company overview, size, industry, revenue estimate (USD)
       ↓
  Surepass GST/CIN → government verification
       ↓
  Probe42 → financial statements, Probe Score, legal records, ROC charges
       ↓
  Combined result written to NormalisedEvent + Company Cache
```

### WHEN — Trigger Conditions

```
Probe42 Company Search:
  TRIGGER when: country_code = "IN" AND enriched_business_flag = true

Probe42 Financial Data:
  TRIGGER when: company found in Probe42 search
                (always request if company exists — financial data is the core value)

Probe42 Legal Records:
  TRIGGER when: company found in Probe42 search
                AND (enriched_company_size > 10 OR Apollo returned revenue > $500K)
                (small micro-businesses rarely have court records worth checking)
```

### HOW — API Integration

**Base URL:** `https://apiportal.probe42.in/v2`
**Auth:** API key in header (header name confirmed after onboarding)
**Method:** GET / POST

**Call 1 — Company Search:**
```http
GET https://apiportal.probe42.in/v2/companies/search
  ?name=Sunita+Catering
  &state=Uttar+Pradesh
  &industry=food
X-API-Key: {PROBE42_KEY}
```
Returns: list of matching companies with CIN, name, incorporation date, Probe Score

**Call 2 — Company Profile (after CIN confirmed):**
```http
GET https://apiportal.probe42.in/v2/companies/{cin}/profile
X-API-Key: {PROBE42_KEY}
```
Returns: registered address, directors, authorized capital, paid-up capital, company status, legal cases, ROC charges

**Call 3 — Financial Data:**
```http
GET https://apiportal.probe42.in/v2/companies/{cin}/financials
X-API-Key: {PROBE42_KEY}
```
Returns: balance sheet, P&L, net worth, EBITDA, revenue, debt-to-equity, employee benefit expenses

Note: Exact endpoint paths above are architecture-design. Final paths confirmed after onboarding with Probe42 support.

### NormalisedEvent Fields Populated

```python
# Financial intelligence — unique to Probe42, no other source provides this
enriched_probe_score: float              # 1.0–5.0 (financial health rating)
enriched_net_worth: int | None           # INR
enriched_annual_turnover_inr: int | None # INR (more precise than GST slab)
enriched_ebitda: int | None              # INR
enriched_debt_to_equity: float | None
enriched_legal_cases_count: int          # active court cases
enriched_roc_charges: int                # ROC charge filings (debt signal)
enriched_epfo_employee_count: int | None # actual employee count from EPFO
enriched_gst_filing_regularity: str | None  # "Regular" | "Irregular" | "Nil Filer"
enriched_beneficial_owner: str | None    # ultimate beneficial owner
enriched_probe42_found: bool             # false if company not in Probe42
```

### Probe Score as a Scoring Signal

The Probe Score maps directly to the Fit dimension:

```python
def probe_score_to_fit_signal(probe_score: float) -> float:
    if probe_score >= 4.0:   return 1.0    # financially strong — high fit
    elif probe_score >= 3.0: return 0.75   # stable
    elif probe_score >= 2.0: return 0.5    # moderate risk
    elif probe_score >= 1.0: return 0.25   # high risk
    else:                    return 0.0    # not found / unrated
```

A company with Probe Score 1 is a credit risk — the sales team should know this before spending time on the lead.

### Source Registry Position

```yaml
IN:
  B2B:
    - source: apollo
    - source: surepass_gstin
    - source: surepass_cin
    - source: probe42          # ← after govt verification, before Tracxn
    - source: tracxn
    - source: newscatcher
    - source: justdial
    - source: indiamart
    - source: serper
```

### Cost and Timing

| Call | Phase | Timing |
|---|---|---|
| Company Search | Phase 2 | Async — parallel with Tracxn |
| Company Profile | Phase 2 | Async — after search returns CIN |
| Financial Data | Phase 2 | Async — after profile confirmed |

**Company Cache TTL:** 90 days for financial data (filed annually). 30 days for profile data.

---

## Tool 3 — Tracxn

### WHY

A CTO at a company that raised a $20M Series B last month is not the same lead as a CTO at a 15-year-old bootstrapped company — even if they send identical messages. The funded company has budget allocated right now and is actively evaluating vendors. The bootstrapped company may take 6 months to approve a purchase. This difference is invisible to Apollo, GST API, and Probe42 — none of them carry funding stage or investor information.

Tracxn is the only source in the stack that answers: is this a startup or growth-stage company, what round are they at, how much have they raised, and who invested in them? These signals are direct indicators of budget availability and buying urgency — especially relevant for B2B SaaS and enterprise software leads.

**The core reason:** Funding stage is a budget availability signal. A recently funded company has money to spend and is under pressure to spend it before the next funding cycle.

### WHAT IT PROVIDES

| Data | Fields | Signal Value |
|---|---|---|
| Company Stage | "Seed", "Early-Stage Funded" (A/B), "Late-Stage Funded" (C+), "Acquired", "Unfunded" | Budget tier |
| Total Funding | Total money raised (USD) | Absolute budget scale |
| Last Funding Round | Round name (Series A/B/C), amount, date, post-money valuation | Recency of budget injection |
| Investors | Investor names, lead investor, investor type | Strategic fit signal |
| Tracxn Score | 0–100 quality score | Company quality proxy |
| Revenue & EBITDA | Latest annual revenue, EBITDA (where available) | Financial scale |
| Employee Count | Latest employee count | Company size |
| News | Latest news mention date, article count | Activity signal |
| Acquisitions | Acquired by whom, when, for how much | Exit status |

### WHERE — Pipeline Step

**Phase 2 (async), Step 8 — Company Resolver, parallel with Probe42**

Tracxn and Probe42 run in parallel — they do not depend on each other. Both are triggered for Indian B2B leads; for non-India B2B leads, Tracxn runs globally while Probe42 is India-only.

```
Step 8 Company Resolver:

  [parallel]
    Probe42  → financial depth (India only)
    Tracxn   → startup/funding intelligence (global)
  [join]
    NormalisedEvent updated with both results
```

### WHEN — Trigger Conditions

```
Tracxn Company Name Search:
  TRIGGER when: enriched_business_flag = true (B2B lead, any country)

Tracxn Funding Details (Transactions API):
  TRIGGER when: company found in Tracxn
                AND stageDetails.stage != "Unfunded"
                (no point querying funding rounds for unfunded companies)

Skip Tracxn entirely:
  WHEN: company_cache HIT for this domain (within 30 days)
  WHEN: Apollo returned company age > 20 years AND no funding flag
        (very established non-startup companies rarely have Tracxn data)
```

### HOW — API Integration (Fully Verified from Official Postman Docs)

**Base URL (Playground):** `https://platform.tracxn.com/api/2.2/playground/`
**Base URL (Production):** `https://platform.tracxn.com/api/2.2/` (remove `/playground`)
**Auth:** `accessToken: {TRACXN_TOKEN}` header
**Method:** POST on all endpoints
**Rate Limits (Playground):** 100 calls/hour, 1,000 calls/day

**Call 1 — Company Name Search:**
```http
POST https://platform.tracxn.com/api/2.2/companies/search
accessToken: {TRACXN_TOKEN}
Content-Type: application/json

{
  "filter": {
    "companyName": ["InMobi"]
  }
}
```
Returns top 10 by relevance: `id`, `name`, `domain`
Take top result `domain`. If 0 results → `enriched_tracxn_found: false`, skip remaining calls.

**Call 2 — Company Full Profile:**
```http
POST https://platform.tracxn.com/api/2.2/companies
accessToken: {TRACXN_TOKEN}
Content-Type: application/json

{
  "filter": {
    "domain": ["inmobi.com"]
  },
  "size": 1
}
```

Key confirmed response fields:

| Response Field | Type | Maps to NormalisedEvent |
|---|---|---|
| `stage` | string | `enriched_company_stage` |
| `foundedYear` | int | `enriched_founded_year` |
| `totalMoneyRaised` | object | `enriched_total_funding_usd` |
| `investorList[].name` | string | `enriched_investors` |
| `latestAnnualRevenue` | object | `enriched_latest_revenue_usd` |
| `latestValuation` | object | `enriched_valuation_usd` |
| `latestFinancialDomainEbitda` | object | `enriched_tracxn_ebitda` |
| `employeeInfo` | object | `enriched_employee_count` |
| `tracxnScore` | double | `enriched_tracxn_score` |
| `newsInfo` | object | `enriched_tracxn_news_date` |
| `location` | object | `enriched_company_hq` |

**Confirmed company stage values:**
```
"Unfunded"
"Seed"
"Early-Stage Funded"    → Series A and Series B
"Late-Stage Funded"     → Series C and above
"Acquired"
```

**Call 3 — Funding Rounds (Transactions API):**
```http
POST https://platform.tracxn.com/api/2.2/transactions
accessToken: {TRACXN_TOKEN}
Content-Type: application/json

{
  "filter": {
    "domain": ["inmobi.com"]
  },
  "sort": [{"sortField": "transactionFundingRoundDate", "order": "DEFAULT"}],
  "size": 3
}
```

Confirmed response fields per round:
- `name` — round name ("Series F")
- `fundingDate.year`, `fundingDate.month`, `fundingDate.day`
- `amount` — round amount
- `currency`
- `investorList[].name`, `investorList[].domain`, `investorList[].isLead`
- `postMoneyValuation.normalizedAmount.value` — post-money valuation (USD)

### NormalisedEvent Fields Populated

```python
enriched_company_stage: str | None         # "Seed" | "Early-Stage Funded" | "Late-Stage Funded"
enriched_total_funding_usd: int | None     # totalMoneyRaised normalized
enriched_last_funding_round: str | None    # "Series F"
enriched_last_funding_date: str | None     # ISO date from fundingDate year/month/day
enriched_last_funding_amount_usd: int | None
enriched_investors: list[str] | None       # investorList[].name
enriched_lead_investor: str | None         # investorList where isLead = "TRUE"
enriched_post_money_valuation_usd: int | None
enriched_tracxn_score: float | None        # 0–100
enriched_founded_year: int | None
enriched_tracxn_found: bool                # false if name search returns 0 results
```

### Funding Stage as a Scoring Signal

```python
def funding_stage_to_budget_signal(stage: str) -> float:
    return {
        "Late-Stage Funded": 1.0,    # Series C+ — significant budget available
        "Early-Stage Funded": 0.75,  # Series A/B — growing budget
        "Seed": 0.5,                 # early-stage — limited budget
        "Unfunded": 0.25,            # bootstrapped — unknown budget
        "Acquired": 0.6,             # depends on acquirer budget
    }.get(stage, 0.0)

def recent_funding_signal(last_funding_date: str) -> float:
    days_since = (today() - parse_date(last_funding_date)).days
    if days_since <= 90:   return 1.0   # funded within 3 months — HOT signal
    elif days_since <= 180: return 0.8
    elif days_since <= 365: return 0.5
    else:                   return 0.2
```

### Source Registry Position

```yaml
ALL_COUNTRIES:
  B2B:
    - source: apollo
    - source: tracxn       # ← global, parallel with Probe42 for India
    - source: newscatcher
    - source: opencorporates
    - source: serper
```

### Cost and Timing

| Call | Phase | Timing |
|---|---|---|
| Company Name Search | Phase 2 | Async — parallel with Probe42 |
| Company Full Profile | Phase 2 | Async — after name search returns domain |
| Transactions (Funding) | Phase 2 | Async — only if stage is funded |

**Company Cache TTL:** 30 days for profile. 7 days for news info from `newsInfo`.

---

## Tool 4 — NewsCatcherAPI

### WHY

No source in the current stack captures what is happening to a company right now. A company that announced a ₹50Cr expansion last month is fundamentally different from a company that announced layoffs last month — even if they have the same GST turnover slab, the same Apollo profile, and the same Probe Score. Buying intent and budget availability are directly affected by recent business events, and news is the fastest signal for those events.

NewsCatcherAPI provides structured access to news articles with NLP analysis — sentiment scoring, named entity recognition, and topic classification — all returned as structured JSON. It allows the system to answer: is this company in the news? For what reason? Is the sentiment positive or negative?

**The core reason:** News is a leading indicator. GST data and Apollo data are lagging indicators — they reflect where a company was 6 months ago. News reflects where they are today.

### WHAT IT PROVIDES

| Endpoint | What It Returns | How We Use It |
|---|---|---|
| `/aggregation_count` | Article count by month for a query | Fast check: is this company in the news at all? Low cost. |
| `/search` | Full articles with NLP — sentiment, topics, named entities | Deep news enrichment after count confirms coverage |
| `/latest_headlines` | Recent headlines filtered by entity | B2C influencer check — is this person in the news? |

**NLP fields returned per article (confirmed):**
- `nlp.sentiment.title` — float -1.0 to 1.0
- `nlp.sentiment.content` — float -1.0 to 1.0
- `nlp.theme` — topic category ("Finance", "Business", "Technology")
- `nlp.summary` — AI summary of article
- `nlp.ner_ORG` — organizations mentioned with count
- `nlp.ner_PER` — people mentioned with count
- `nlp.iptc_tags_name` — IPTC media topic tags

### WHERE — Pipeline Step

**Phase 2 (async), Step 8 — Company Resolver, after company identity confirmed**

NewsCatcherAPI runs after Apollo and Tracxn have confirmed the company exists. Without a confirmed company name, the news search query is unreliable.

```
Step 8 — Company Resolver sequence:

  Apollo → company confirmed, name locked
       ↓
  Tracxn → funding stage retrieved
       ↓
  NewsCatcherAPI → news intelligence (parallel with Probe42)
       ↓
  All results merged into NormalisedEvent
```

### WHEN — Trigger Conditions

```
/aggregation_count (cheap check first):
  TRIGGER when: company confirmed by Apollo or Tracxn
                AND (company_size > 50 OR funding_stage is not null)
  SKIP when: company is a micro-business (< 10 employees) — unlikely to be in news

/search (full article fetch):
  TRIGGER when: aggregation_count returns total_hits > 0
  SKIP when: aggregation_count returns total_hits = 0 — no articles exist, save the cost

/latest_headlines (B2C path):
  TRIGGER when: B2C lead AND follower_count > 10,000 (public figure / influencer)
```

### HOW — API Integration (Fully Verified from Official Docs)

**Base URL:** `https://v3-api.newscatcherapi.com/api`
**Auth:** `x-api-token: {NEWSCATCHER_KEY}` header
**Method:** POST (recommended for production — avoids URL length limits)

**Call 1 — Aggregation Count (always first):**
```http
POST https://v3-api.newscatcherapi.com/api/aggregation_count
x-api-token: {NEWSCATCHER_KEY}
Content-Type: application/json

{
  "q": "\"InMobi\"",
  "from_": "2026-02-16",
  "to_": "2026-05-16",
  "aggregation_by": "month",
  "lang": "en",
  "countries": "IN"
}
```

Confirmed response:
```json
{
  "status": "success",
  "total_hits": 43,
  "aggregations": {
    "aggregation_count": [
      {"time_frame": "2026-02-01 00:00:00", "article_count": 12},
      {"time_frame": "2026-03-01 00:00:00", "article_count": 18},
      {"time_frame": "2026-04-01 00:00:00", "article_count": 13}
    ]
  }
}
```
If `total_hits = 0` → stop here, set `enriched_news_count_90d: 0`, skip Call 2.

**Call 2 — Full Search (only if total_hits > 0):**
```http
POST https://v3-api.newscatcherapi.com/api/search
x-api-token: {NEWSCATCHER_KEY}
Content-Type: application/json

{
  "q": "\"InMobi\"",
  "lang": "en",
  "countries": "IN,US",
  "from_": "2026-02-16",
  "to_": "2026-05-16",
  "sort_by": "relevancy",
  "page_size": 5,
  "include_nlp_data": true,
  "ORG_entity_name": "InMobi"
}
```

Confirmed key request parameters:

| Parameter | Type | What We Set |
|---|---|---|
| `q` | string | Company name in quotes for exact match |
| `ORG_entity_name` | string | Confirms NLP identified the org — reduces noise |
| `from_` / `to_` | ISO 8601 | 90-day window |
| `countries` | string | Lead's country + "US" (English press covers Indian companies) |
| `lang` | string | "en" for English, "hi" for Hindi news |
| `include_nlp_data` | boolean | true — needed for sentiment + topics |
| `sort_by` | string | "relevancy" |
| `page_size` | integer | 5 — top 5 articles is sufficient |

Confirmed response fields used:
```json
{
  "total_hits": 43,
  "articles": [
    {
      "title": "InMobi raises $100M",
      "published_date": "2026-04-12T10:30:00Z",
      "name_source": "Economic Times",
      "country": "IN",
      "nlp": {
        "theme": "Finance",
        "summary": "InMobi secured $100M in Series F funding...",
        "sentiment": {
          "title": 0.82,
          "content": 0.74
        },
        "ner_ORG": [{"entity_name": "InMobi", "count": 8}]
      }
    }
  ]
}
```

### NormalisedEvent Fields Populated

```python
enriched_news_count_90d: int                # total_hits from aggregation_count
enriched_news_sentiment_avg: float          # average nlp.sentiment.content across articles
enriched_news_sentiment_label: str          # "positive" | "negative" | "neutral" | "mixed"
enriched_news_themes: list[str]             # nlp.theme values across top articles
enriched_news_top_headline: str | None      # title of highest-scoring article
enriched_news_top_source: str | None        # name_source of top article
enriched_news_top_date: str | None          # published_date of most recent article
enriched_news_monthly_trend: list[dict]     # aggregation_count array
```

### News Sentiment as a Scoring Signal

```python
def news_sentiment_to_context_signal(
    sentiment_avg: float,
    themes: list[str]
) -> tuple[float, str]:
    boost_themes = {"funding", "expansion", "award", "partnership", "launch"}
    risk_themes = {"layoffs", "bankruptcy", "lawsuit", "fraud", "restructuring"}

    theme_set = {t.lower() for t in themes}
    has_boost = bool(theme_set & boost_themes)
    has_risk = bool(theme_set & risk_themes)

    if has_boost and sentiment_avg > 0.5:
        return 1.0, "company_momentum_positive"
    elif has_risk and sentiment_avg < -0.3:
        return 0.1, "company_under_stress"
    elif sentiment_avg > 0.2:
        return 0.7, "neutral_positive"
    else:
        return 0.5, "neutral"
```

### Cost and Timing

| Call | Phase | Timing | Cost |
|---|---|---|---|
| `/aggregation_count` | Phase 2 | Async — after company confirmed | Subscription |
| `/search` | Phase 2 | Async — only if count > 0 | Subscription |

**Company Cache TTL:** 7 days — news is time-sensitive. Do not cache longer.

---

## Tool 5 — Serper.dev

### WHY

Even with Apollo, Surepass, Probe42, Tracxn, and NewsCatcherAPI, some leads will return zero data from all structured sources. A hyper-local caterer, a freelance consultant, a tiny family business — these exist outside every database. Without any enrichment, the lead scores entirely on the message text alone, with `lead_completeness` near zero and `needs_review: true` in every case.

Serper provides structured Google Search results as JSON. When all structured APIs fail, a single Google search often surfaces a JustDial listing, a LinkedIn profile, a company website, or an IndiaMART page that gives the system just enough signal to improve lead completeness and give the salesperson a starting point.

Serper is also used as a last-resort news source when NewsCatcherAPI returns zero results — the `/news` endpoint returns Google News results for the same query.

**The core reason:** Zero enrichment is always worse than partial enrichment. Serper is the safety net that ensures every lead gets at least something.

### WHAT IT PROVIDES

| Endpoint | What It Returns | How We Use It |
|---|---|---|
| `/search` | Organic Google results: title, link, snippet, knowledge graph | Find company website, JustDial, IndiaMART, LinkedIn |
| `/news` | Google News results for a query | Fallback news source when NewsCatcherAPI returns 0 |
| `/maps` | Google Maps results for a business name + city | Verify physical business presence, get category and rating |

### WHERE — Pipeline Step

**Phase 2 (async), Step 8/9 — last-resort fallback after all structured sources exhausted**

```
Source Registry fallback chain:

  Apollo → miss
  Surepass → miss (GSTIN not found, CIN not found)
  Probe42 → miss (company not in database)
  Tracxn → miss (not a startup)
        ↓
  [all structured sources exhausted]
        ↓
  Serper /search → Google search for company/person
  Serper /maps   → Google Maps for physical business verification
  Serper /news   → Google News fallback if NewsCatcherAPI also returned 0
```

### WHEN — Trigger Conditions

```
/search — B2B fallback:
  TRIGGER when: Apollo returned no company match
                AND Probe42 returned no company match
                AND company_verified = false

/search — B2C fallback:
  TRIGGER when: enriched_instagram_handle is null
                AND enriched_truecaller_bio is null
                AND enriched_topic_affinity is null

/news — news fallback:
  TRIGGER when: enriched_news_count_90d = 0 (NewsCatcherAPI returned nothing)
                AND company_size > 20

/maps — physical business verification:
  TRIGGER when: B2B lead
                AND company not found in Apollo, Probe42, or Tracxn
                AND city/location available from message

NEVER trigger Serper when: company_cache HIT exists
```

### HOW — API Integration

**Base URL:** `https://google.serper.dev`
**Auth:** `X-API-KEY: {SERPER_KEY}` header
**Method:** POST
**Pricing:** $50 for 50,000 queries (~$0.001/call). 2,500 free queries on signup.

**Call 1 — B2B Company Fallback:**
```http
POST https://google.serper.dev/search
X-API-KEY: {SERPER_KEY}
Content-Type: application/json

{
  "q": "\"Sunita Catering\" Lucknow site:justdial.com OR site:indiamart.com OR site:linkedin.com",
  "gl": "in",
  "hl": "en",
  "num": 5
}
```

**Call 2 — B2C Person Fallback:**
```http
POST https://google.serper.dev/search
X-API-KEY: {SERPER_KEY}
Content-Type: application/json

{
  "q": "\"Riya Sharma\" Pune instagram OR yoga",
  "gl": "in",
  "num": 5
}
```

**Call 3 — Google Maps Business Check:**
```http
POST https://google.serper.dev/maps
X-API-KEY: {SERPER_KEY}
Content-Type: application/json

{
  "q": "Sunita Catering Lucknow",
  "gl": "in"
}
```

**Call 4 — News Fallback:**
```http
POST https://google.serper.dev/news
X-API-KEY: {SERPER_KEY}
Content-Type: application/json

{
  "q": "InMobi funding OR expansion OR layoffs",
  "gl": "in",
  "tbs": "qdr:m3"
}
```

**Result extraction logic (runs on Serper response):**
```python
def extract_from_serper(results: list[dict]) -> dict:
    extracted = {}
    for r in results:
        link = r.get("link", "")
        if "justdial.com" in link:
            extracted["justdial_url"] = link
            extracted["justdial_snippet"] = r.get("snippet")
        elif "indiamart.com" in link:
            extracted["indiamart_url"] = link
        elif "linkedin.com/company" in link:
            extracted["linkedin_company_url"] = link
        elif "linkedin.com/in/" in link:
            extracted["linkedin_person_url"] = link
        elif "instagram.com" in link:
            extracted["instagram_url"] = link
    extracted["web_presence"] = len(extracted) > 0
    extracted["top_snippet"] = results[0].get("snippet") if results else None
    return extracted
```

### NormalisedEvent Fields Populated

```python
enriched_web_presence: bool               # true if any result found
enriched_justdial_url: str | None         # JustDial listing URL
enriched_indiamart_url: str | None        # IndiaMART listing URL
enriched_linkedin_company_url: str | None
enriched_linkedin_person_url: str | None
enriched_google_maps_rating: float | None # from /maps endpoint
enriched_google_maps_category: str | None # business category from Maps
enriched_google_snippet: str | None       # best matching snippet
enriched_serper_news_headline: str | None # from /news fallback
```

### Cost and Timing

| Call | Phase | Timing | Cost |
|---|---|---|---|
| `/search` B2B | Phase 2 | Async — only after all structured APIs fail | ~$0.001 |
| `/search` B2C | Phase 2 | Async — only after identity APIs fail | ~$0.001 |
| `/maps` | Phase 2 | Async — parallel with /search | ~$0.001 |
| `/news` | Phase 2 | Async — only if NewsCatcher returned 0 | ~$0.001 |

**Company Cache TTL:** 14 days for Serper results (web content changes more often than govt data).

---

## Complete Updated Source Registry

```yaml
# source_registry.yaml — full updated configuration

IN:
  B2B:
    - source: apollo
      phase: sync
      step: [7_disambiguate, 8_company, 9_person]
      trigger: always

    - source: surepass_gstin
      phase: sync
      step: 8_company
      trigger: gstin_available OR b2b_india

    - source: surepass_cin
      phase: sync
      step: 8_company
      trigger: cin_available OR company_name_known

    - source: surepass_pan
      phase: async
      step: 8_company
      trigger: gstin_null AND pan_available

    - source: probe42
      phase: async
      step: 8_company
      trigger: b2b_india AND company_name_known

    - source: tracxn
      phase: async
      step: 8_company
      trigger: b2b_any_country

    - source: newscatcher
      phase: async
      step: 8_company
      trigger: company_confirmed AND (company_size > 50 OR funding_stage_known)

    - source: justdial
      phase: async
      step: 8_company
      trigger: company_size_lt_50

    - source: indiamart
      phase: async
      step: 8_company
      trigger: b2b_trading_signals

    - source: serper
      phase: async
      step: 8_company
      trigger: all_structured_sources_failed

    - source: opencorporates
      phase: async
      step: 8_company
      trigger: cin_not_found

  B2C:
    - source: truecaller
      phase: sync
      step: tier2
      trigger: phone_available

    - source: google_places
      phase: sync
      step: tier2
      trigger: phone_available

    - source: instagram_graph
      phase: async
      step: 9_person
      trigger: igsid_available

    - source: apify_instagram
      phase: async
      step: 9_person
      trigger: public_account

    - source: newscatcher
      phase: async
      step: 9_person
      trigger: b2c_influencer AND follower_count_gt_10000

    - source: serper
      phase: async
      step: 9_person
      trigger: all_b2c_identity_sources_failed

GB:
  B2B:
    - source: apollo
    - source: companies_house
    - source: tracxn
    - source: newscatcher
    - source: opencorporates
    - source: serper

US:
  B2B:
    - source: apollo
    - source: sec_edgar
    - source: tracxn
    - source: newscatcher
    - source: opencorporates
    - source: serper

EU:
  B2B:
    - source: apollo
    - source: vies
    - source: tracxn
    - source: newscatcher
    - source: opencorporates
    - source: serper

AE:
  B2B:
    - source: apollo
    - source: tracxn
    - source: newscatcher
    - source: opencorporates
    - source: serper
```

---

## Complete Updated NormalisedEvent Schema

All new fields added by the five tools:

```python
# ── Surepass fields ──────────────────────────────────────────────
enriched_gst_status: str | None              # "Active" | "Cancelled" | "Suspended"
enriched_business_nature: list[str] | None   # ["Wholesale Business"]
enriched_incorporation_date: str | None      # ISO date
enriched_registered_address: str | None
enriched_directors: list[str] | None
enriched_pan_verified: bool
enriched_msme_registered: bool
enriched_msme_category: str | None           # "Micro" | "Small" | "Medium"

# ── Probe42 fields ───────────────────────────────────────────────
enriched_probe_score: float | None           # 1.0–5.0
enriched_net_worth: int | None               # INR
enriched_annual_turnover_inr: int | None     # INR
enriched_ebitda: int | None                  # INR
enriched_debt_to_equity: float | None
enriched_legal_cases_count: int              # default 0
enriched_roc_charges: int                    # default 0
enriched_epfo_employee_count: int | None
enriched_gst_filing_regularity: str | None  # "Regular" | "Irregular"
enriched_beneficial_owner: str | None
enriched_probe42_found: bool

# ── Tracxn fields ────────────────────────────────────────────────
enriched_company_stage: str | None           # "Seed" | "Early-Stage Funded" | "Late-Stage Funded"
enriched_total_funding_usd: int | None
enriched_last_funding_round: str | None      # "Series F"
enriched_last_funding_date: str | None       # ISO date
enriched_last_funding_amount_usd: int | None
enriched_investors: list[str] | None
enriched_lead_investor: str | None
enriched_post_money_valuation_usd: int | None
enriched_tracxn_score: float | None          # 0–100
enriched_founded_year: int | None
enriched_tracxn_found: bool

# ── NewsCatcherAPI fields ────────────────────────────────────────
enriched_news_count_90d: int                 # default 0
enriched_news_sentiment_avg: float | None    # -1.0 to 1.0
enriched_news_sentiment_label: str | None    # "positive" | "negative" | "neutral" | "mixed"
enriched_news_themes: list[str] | None
enriched_news_top_headline: str | None
enriched_news_top_source: str | None
enriched_news_top_date: str | None
enriched_news_monthly_trend: list[dict] | None

# ── Serper fields ─────────────────────────────────────────────────
enriched_web_presence: bool                  # default false
enriched_justdial_url: str | None
enriched_indiamart_url: str | None
enriched_linkedin_company_url: str | None
enriched_linkedin_person_url: str | None
enriched_google_maps_rating: float | None
enriched_google_maps_category: str | None
enriched_google_snippet: str | None
enriched_serper_news_headline: str | None
```

---

## Updated Cost Model

```
Per-lead cost at steady state after all 5 tools added:

B2C India lead (WhatsApp, no public social):
  Truecaller:           ~$0.001
  Google Places:        $0.017
  Surepass:             TBD (post support call)
  NewsCatcherAPI:       subscription / per-call
  Serper (if fallback): ~$0.001
  ─────────────────────────────
  Estimated:            ~$0.025–0.04/lead

B2B India lead (full investigation):
  Truecaller:           ~$0.001
  Google Places:        $0.017
  Apollo:               ~$0.01–0.03
  Surepass GSTIN:       TBD
  Surepass CIN:         TBD
  Probe42:              TBD (enterprise pricing)
  Tracxn:               volume licensing
  NewsCatcherAPI:        subscription
  Serper (if fallback): ~$0.001
  ─────────────────────────────
  Estimated:            ~$0.10–0.20/lead (before caching)

Identity graph cache effect (Month 3+):
  40% cache hit rate → ~35–40% cost reduction
  60% cache hit rate → ~50–60% cost reduction

At 300 leads/day mixed B2C/B2B:
  Current stack:          ~$180–270/month
  After 5 tools added:    ~$300–450/month (estimate pending vendor pricing)
  After cache matures:    ~$180–280/month
```

---

## Next Steps — What to Confirm with Each Vendor

### Surepass Support Call
Ask for:
- Postman collection or API reference with exact endpoint paths
- Sandbox/test environment credentials
- Pricing per API call (GST, CIN, PAN to Company specifically)
- Rate limits per tier
- Webhook support for async verifications

### Probe42 Support Call
Ask for:
- API v2 documentation with endpoint paths and response schemas
- Sandbox access
- Pricing model (per call vs subscription)
- Rate limits
- Whether financial data (balance sheet) is a separate endpoint or bundled

### Serper.dev
No support call needed:
- Sign up free at `serper.dev/signup` → 2,500 free queries
- Full documentation available inside dashboard after login

---

## Open Questions

1. Surepass exact endpoint paths — confirmed after API key onboarding
2. Probe42 exact endpoint paths — confirmed after API v2 sandbox access
3. Surepass pricing per call — affects cost model
4. Probe42 pricing model — per call vs flat subscription affects caching strategy
5. Whether Probe42 financial data requires a separate endpoint call or is bundled in profile
6. Serper `/maps` availability in India — Google Maps coverage for Indian SMBs needs validation
7. NewsCatcherAPI subscription tier — which tier covers 300 company searches/day

---

## Relationship to Other Documents

- [[analyses/lead-enrichment-architecture]] — Original enrichment architecture; this document adds 5 tools on top of that foundation. Signal separation principle and two-phase model from that document remain unchanged.
- [[analyses/global-data-collection-architecture]] — Source Registry pattern and 13-step pipeline defined there; this document extends the Source Registry config for all 5 new tools.
- [[analyses/signal-detection-rule-spec]] — New extractor types needed: `probe_score_threshold`, `funding_stage_match`, `news_sentiment_threshold`, `recent_funding_recency`. These must be added to the extractor vocabulary and Persona Agent Step 3.
- [[analyses/orchestration-layer-spec]] — Pipeline 1 orchestration unchanged; new tools run inside existing Step 8 Company Resolver slot.
- [[analyses/inngest-function-design]] — The Phase 2 investigation Inngest function needs to be extended to include Probe42, Tracxn, and NewsCatcherAPI calls in the parallel fan-out step.
- [[analyses/rating-agent-spec]] — Rating Agent INPUT_SCHEMA must be extended to include new NormalisedEvent fields from all 5 tools.
