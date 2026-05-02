---
type: analysis
question: "How does the system collect and understand lead data globally, across B2B and B2C, for any country, starting from just a name and phone number?"
date: 2026-05-03
tags: [data-collection, enrichment, b2b, b2c, global, jurisdiction, message-parser, company-resolver, conversation-threading, account-intelligence, no-scraping, apollo, truecaller, mca, companies-house, registry-pattern]
sources_consulted:
  - "[[analyses/lead-enrichment-architecture]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/signal-detection-rule-spec]]"
  - "[[analyses/channel-integration-layer]]"
  - "[[analyses/tech-stack-research]]"
status: COMPLETE — supersedes India-specific provider stack in lead-enrichment-architecture (2026-04-30); global registry approach replaces hard-coded per-region logic
---

# Global Lead Data Collection Architecture

**Question:** How does the system collect and understand lead data globally, across B2B and B2C, for any country, starting from just a name and phone number?
**Date:** 2026-05-03

---

## The Plain-English Version First

When someone sends a message to a tenant's WhatsApp, Instagram, or LinkedIn, the system needs to answer three questions before it can score the lead:

1. **Who is this person?** (name, role, which company they work for)
2. **What kind of lead is this?** (are they a business buying for their company, or a person buying for themselves?)
3. **What do they want?** (is their intent clear, or do we need to ask a follow-up?)

The challenge is that different leads send very different messages. Some say their company name. Some write in Hindi. Some only say "hello." Some are from India, some from the UK, some from the UAE. The system has to handle all of this without ever scraping a website illegally, without requiring code changes when a new country is added, and without wasting expensive AI calls on things that can be figured out for free.

This document explains how the system does that — step by step, with real examples.

> **Important note on scraping:** The system uses only official government APIs (MCA, Companies House, GST), licensed commercial data APIs (Apollo.io, Truecaller for Business), and open data aggregators (OpenCorporates). It does not scrape any website. All data sources are either official APIs or providers who license and serve the data through their own API.

---

## The Revised LLM Call Principle

The original system principle was "1 LLM call per lead (Scoring Agent only)." This document introduces a second, very cheap LLM call — the **Message Parser** — which uses Claude Haiku (not Sonnet). Haiku costs roughly 15× less than Sonnet.

**Revised principle:**
> One Sonnet call per lead (Scoring Agent only). Haiku is allowed for cheap extraction tasks such as Message Parsing. No other LLM calls on the data collection path.

The reason Haiku is needed here is simple: real messages from real people contain typos, are written in Hindi or Hinglish, use informal language, and cannot be reliably parsed by simple code. A cheap LLM handles this better than any regex.

---

## The Full Flow at a Glance

```
Message arrives on channel (WhatsApp / Instagram / LinkedIn)
              │
    ┌─────────▼──────────┐
    │   Pre-Filter Gate  │  ← Is this even a real message?
    └─────────┬──────────┘
              │ real message
    ┌─────────▼──────────┐
    │   Message Parser   │  ← What did they say? (Haiku LLM)
    └─────────┬──────────┘
              │ structured data
    ┌─────────▼──────────┐
    │  Free Signal Score │  ← B2B or B2C? (free, no API)
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │ Jurisdiction Check │  ← Which country? (free, phone prefix)
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │  Account Graph     │  ← Has this company contacted us before?
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │ Conversation Thread│  ← Is this a reply to an existing lead?
    └─────────┬──────────┘
              │ new lead
    ┌─────────▼──────────┐
    │   Company Cache    │  ← Have we looked up this company recently?
    └─────────┬──────────┘
              │ cache miss
    ┌─────────▼──────────┐
    │Company Disambiguator│ ← Which company exactly?
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │  Company Resolver  │  ← Look up company data (API chain)
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │  Person Resolver   │  ← Look up person data + verify
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │Location Reconcile  │  ← Separate person city from company HQ
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   Consent Gate     │  ← Are we allowed to enrich this lead?
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   Intent Gate      │  ← Is the intent clear? If not, ask.
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │  Scoring Agent     │  ← The one Sonnet call per lead
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   Delivery Layer   │  ← Show result to salesperson
    └────────────────────┘
```

---

## Every Step Explained

---

### Step 0 — Pre-Filter Gate

**What it does:** Before touching any API or LLM, the system checks whether this is even a real message worth processing.

**What gets filtered out:**
- Messages with fewer than 10 characters ("hi", "ok", "?", "👋")
- Messages that are only emojis or punctuation
- Repeated identical messages (spam)
- Known bot patterns

**Why this matters:** Without this gate, someone sending "hello" would trigger the Message Parser, the Signal Scorer, and potentially an Apollo API call — wasting money on nothing.

**Cost:** Zero. Pure code logic. Runs in milliseconds.

---

### Step 1 — Message Parser (Haiku LLM Call)

**What it does:** Reads the raw message and pulls out structured information — who the person is, what company they mentioned, what role they have, where they are, and what they seem to want.

**Why a small LLM and not code?** Real messages are messy. People write in Hinglish, make spelling mistakes, use informal language, and don't follow any template. A lightweight LLM handles all of this far better than any rule-based approach.

**What comes out:**
```
name:                  "Aishekh Prasad"
company:               "InMobi"
role:                  "CTO"
location_mentioned:    "Lucknow"
intent_text:           "I want to buy something"
business_ownership:    false  ← did they say "I run a business"?
language_detected:     "en"
```

**What the Message Parser is NOT doing:** It is not scoring the lead. It is not deciding if the lead is good or bad. It is only extracting raw facts from the message text.

---

### Step 2 — Free Signal Scorer

**What it does:** Uses what the Message Parser extracted to make a first guess about whether this is a B2B lead (business buying from a business) or a B2C lead (individual buying for personal use).

**How it scores — no API needed:**

| Signal | B2B Points | B2C Points |
|---|---|---|
| Company name mentioned | +3 | — |
| Job title mentioned (CEO, CTO, Manager, etc.) | +2 | — |
| Business ownership phrase ("I run a", "my company", "our firm") | +3 | — |
| Purchase phrase ("bulk order", "invoice", "GST bill") | +3 | — |
| Lead came from LinkedIn | +2 | — |
| Lead came from Instagram | — | +2 |
| Personal purchase phrase ("for myself", "one piece", "personal use") | — | +2 |

**Decision rule:**
- Score +2 or above → **B2B confirmed** (skip identity API call for classification)
- Score -1 or below → **B2C confirmed**
- Score 0 or unclear → continue to identity API which resolves it

**Cost:** Zero. No API call. Runs in milliseconds.

---

### Step 3 — Jurisdiction Classifier

**What it does:** Figures out which country this lead is from. This determines which data sources the system will use to look them up.

**How:**
- Phone number prefix → country code (the library `libphonenumber` handles 240+ countries, takes milliseconds)
- If GST number format is present in the message → India confirmed
- If VAT number format present → EU country identified
- Location mentioned ("Lucknow") → used as a supporting signal, not the primary one

**Output:** `country_code: "IN"` (India), `"GB"` (UK), `"US"`, `"AE"` (UAE), etc.

**Cost:** Zero. Library call, no API, no network.

---

### Step 4 — Account Graph Check

**What it does:** Before looking up any new data, the system checks if other people from the same company have already contacted the tenant.

**Why this matters:** Five people from the same company reaching out in one week is a much stronger buying signal than one person with a vague message. The Scoring Agent needs to know this.

**What gets passed forward:**
```
account_engagement:
  company: "InMobi"
  leads_this_month: 3
  roles_seen: ["CTO", "VP Sales", "Finance Manager"]
  engagement_signal: "HIGH"
```

If `leads_this_month > 1`, this gets injected into the Scoring Agent's context so it can factor in account-level buying intent, not just individual message intent.

**Cost:** Simple database query. Free.

---

### Step 5 — Conversation Thread Check

**What it does:** Checks whether this message is a fresh lead or a reply to an existing conversation.

**The problem it solves:** When the system sends an automated follow-up ("Hi Aishekh, what specifically are you looking for?") and Aishekh replies, that reply will arrive as a new incoming message. Without this check, the system would create a second lead record for the same person — losing the connection to the original.

**How it works:**
- Every lead is stored with a `conversation_id` tied to the channel thread (WhatsApp thread, Instagram DM thread, etc.)
- Incoming message on an existing thread → appended to the original lead record
- Pipeline re-runs with the full combined context: original message + follow-up reply
- Score upgrades if the new message contains clearer intent

**If it's a new thread:** Continue the pipeline normally.

**Cost:** Database lookup. Free.

---

### Step 6 — Company Cache Check

**What it does:** Before calling any external API, checks if the system already looked up this company recently.

**Why:** If 50 leads from InMobi arrive this week, the system should look up InMobi's company profile once, not 50 times. The company's founding year, directors, and industry don't change week to week.

**Cache key:** Company name + country code (not just company name — there may be an InMobi in multiple countries)

**Cache TTL (how long data is kept):**
- Official registry data (MCA, Companies House): 30 days — regulatory data changes slowly
- Website intelligence: 14 days — website content changes more often

**Cache hit:** Serve the stored company profile, skip Steps 7–8, continue from Step 9.

**Cache miss:** Continue to Step 7.

**Cost:** Database lookup. Free.

---

### Step 7 — Company Disambiguator

**What it does:** Searches for the company in the database and checks whether there is exactly one match or multiple.

**Why this is needed:** Many company names are shared. "Axis" could be Axis Bank (India, 70,000 employees), Axis Communications (Sweden, networking), Axis Capital (India, finance), or dozens of others. Picking the wrong one and enriching the lead against it is worse than having no data at all.

**How it works:**
- Apollo.io is searched for the company name + country
- If one clear match returns with confidence ≥ 80% → proceed
- If multiple matches return → the top 2 are surfaced to the salesperson as a flag: "Which company did you mean?"
- The pipeline continues with a `company_unverified: true` flag set until the salesperson confirms

**Cost:** One Apollo.io API call — approximately $0.01–0.03.

---

### Step 8 — Company Resolver

**What it does:** Looks up the company's details — industry, size, founding year, revenue estimate, directors — using the right sources for the jurisdiction.

**The registry pattern (no hard-coded logic):** Instead of writing code that says "if India, go to MCA," the system reads a configuration file called the Source Registry. The registry maps every country to an ordered list of data sources. When a source is unavailable or its API changes, ops updates the config file — no code changes, no redeployment.

**Source registry example for India B2B:**
```
Country: India (IN) | Lead type: B2B
Sources (tried in order):
  1. Apollo.io API         → company overview, size, industry, revenue estimate
  2. MCA21 API (official)  → directors, company type, authorized capital, year founded
  3. GST Portal API        → turnover slab, business nature, GST status
  4. OpenCorporates API    → fallback if MCA is unavailable
```

**What "tried in order" means:** The system tries Source 1 first. If it succeeds, it moves on. If Source 1 fails (API is down, company not found), it automatically tries Source 2, then Source 3. This is the fallback chain. The pipeline never fails hard because of a single source being unavailable.

**SMB handling:** If the company is a small local business not found in Apollo or MCA by name (very common for Indian SMBs), the system does not fail. It records what it found, sets `lead_completeness` lower, and flags the profile as needing additional qualification. The salesperson will see a note: "Company details could not be verified — ask for GST number in conversation."

---

### Step 9 — Person Resolver

**What it does:** Looks up the specific person — their confirmed job title, how long they've been at the company, their professional background.

**How:**
- Apollo.io person search: name + company name → returns LinkedIn-sourced profile
- Cross-reference: does Apollo's phone number for this person match the phone the message came from? If yes → `identity_verified: true`. If no → `identity_verified: false`, flag shown to salesperson.
- Staleness check: if Apollo's data for this person was last updated more than 6 months ago → `role_unverified: true`, note shown: "Title sourced from LinkedIn as of [date] — confirm in conversation."

**Why staleness matters:** People change jobs. If Aishekh Prasad left InMobi 3 months ago but Apollo hasn't updated yet, the system would present him as InMobi's CTO. The salesperson calls thinking they're speaking to an InMobi decision-maker — they're not.

---

### Step 10 — Location Reconciliation

**What it does:** Separates the person's city from the company's city. These are often different and often confused.

**The problem:** The message says "from InMobi Lucknow." The system extracts location "Lucknow." But InMobi's headquarters is Bangalore. If the system assigns Lucknow to InMobi, it creates a wrong company record.

**How it resolves:** After Apollo returns InMobi's known HQ (Bangalore), the system compares:
- Company HQ from Apollo: Bangalore
- Location from message: Lucknow
- **Decision:** Lucknow = person's city, not company city

**Output:**
```
lead_location:  "Lucknow, Uttar Pradesh, India"
company_hq:     "Bangalore, Karnataka, India"
```

These are stored as separate fields. Neither overwrites the other.

---

### Step 11 — Consent Gate

**What it does:** Checks whether the tenant's privacy policy allows the system to look up personal data about this lead, given which country the lead is from.

**Why:** India's Digital Personal Data Protection (DPDP) Act 2023 and Europe's GDPR both have rules about when you can enrich someone's personal data. For B2B leads, "legitimate business interest" generally applies — but the tenant must have documented this in their settings.

**How it works:** The system reads `tenant_policy.consent_mode` for the lead's country:
- If the tenant has configured their consent settings → proceed
- If the tenant hasn't configured consent for this jurisdiction → pause enrichment, flag for ops

This is not a blocker today at MVP scale, but it must be built into the pipeline from day one. Retrofitting compliance is far more expensive than building it in.

---

### Step 12 — Intent Gate

**What it does:** Checks whether the lead's message contains enough information to score their intent — or whether a follow-up question is needed first.

**The problem it solves:** A CTO of a large company who says "I want to buy something" is a high-value lead with almost no intent signal. If the system scores them now, their Intent score is very low and they land in WARM. But if the system asks one clarifying question — "What specifically are you looking for?" — and they reply with "500 enterprise licenses by Q3 with a ₹20L budget," that lead becomes HOT.

**The decision logic:**
- If `intent_specificity = very_low` AND `fit_score = HIGH` → send automated clarification via the same channel, set lead status to `awaiting_clarification`
- While `awaiting_clarification`: salesperson sees the lead card but cannot send a manual message (prevents the lead receiving two messages from the same company)
- On reply: pipeline re-runs with the combined context. Score upgrades automatically.
- If no reply within 24 hours: score the lead anyway with a completeness penalty applied

**Tenant configuration option:** Some tenants may prefer to always score immediately and let the salesperson follow up manually. This is a tenant-level setting.

---

### Step 13 — Scoring Agent (The One Sonnet Call)

At this point, the system has a complete picture of the lead. The Scoring Agent receives:
- The full company profile (industry, size, founded year, revenue estimate, directors)
- The person profile (role, seniority, tenure, identity verified or not)
- The intent text (what they said they want)
- The account engagement signal (how many others from this company contacted the tenant)
- The tenant's Persona Object (who the tenant is, who their ideal customer is)

The Scoring Agent evaluates the lead across five dimensions — Fit, Intent, Engagement, Behaviour, Context — and produces a score from 0–100, a bucket (HOT / WARM / COLD), a plain-English explanation, and a `lead_completeness` value.

Full specification: [[analyses/rating-agent-spec]]

---

## The Global Source Map (No-Scraping, API Only)

### Universal — All Regions, All Lead Types

| Source | What it gives | Type |
|---|---|---|
| Apollo.io | Company overview, size, industry, revenue estimate, person's role and history | Licensed commercial API |
| OpenCorporates | Corporate registration data across 140+ countries | Licensed aggregator API |
| People Data Labs (PDL) | Personal identity, phone-to-profile matching | Licensed commercial API |

Apollo is the global spine. It covers enough ground that for most leads in most countries, one Apollo call gives you enough to score. The sources below add depth and official verification on top of it.

---

### India (IN)

| Source | What it gives | Type |
|---|---|---|
| Truecaller for Business | Phone → name, business/personal tag, business category | Official partner API |
| MCA21 API | Directors, company type, authorized capital, year incorporated | Official government API (free) |
| GST Portal API | Turnover slab, business nature, GST registration status | Official government API (free) |
| Apollo.io | Company overview, person's LinkedIn profile | Licensed commercial API |

**India note:** The phone number is India's strongest identity signal. Truecaller has over 300 million Indian phone numbers tagged as business or personal. For B2C leads in India, Truecaller alone gives more reliable data than most other sources.

---

### United Kingdom (GB)

| Source | What it gives | Type |
|---|---|---|
| Companies House API | Full filing history, SIC industry code, directors, accounts | Official government API (free, excellent) |
| Apollo.io | Company overview, person profile | Licensed commercial API |

**UK note:** Companies House is the best free corporate registry API in the world. It gives complete, accurate, current data. For UK B2B leads, this is all you need for company verification.

---

### United States (US)

| Source | What it gives | Type |
|---|---|---|
| SEC EDGAR API | Financials, filings (public companies only) | Official government API (free) |
| OpenCorporates | Private company registration (aggregates all 50 states) | Aggregator API |
| Apollo.io | Company overview, person profile | Licensed commercial API |

**US note:** Most US private companies are registered in Delaware, regardless of where they operate. OpenCorporates aggregates all 50 state databases into one API call.

---

### European Union (EU)

| Source | What it gives | Type |
|---|---|---|
| VIES API | VAT number validation, registered country | Official EU API (free) |
| OpenCorporates | Country-level registry data | Aggregator API |
| Apollo.io | Company overview, person profile | Licensed commercial API |

**EU note:** If the lead provides a VAT number, VIES tells you in milliseconds whether the company is VAT-registered and in which EU country. This also confirms jurisdiction for routing.

---

### Middle East (UAE, Saudi Arabia, Bahrain, Qatar)

| Source | What it gives | Type |
|---|---|---|
| Apollo.io | Company overview, person profile (LinkedIn-sourced) | Licensed commercial API |
| OpenCorporates | Where available | Aggregator API |

**Middle East note:** No official public APIs exist for corporate registries in the Middle East. Apollo (sourced from LinkedIn) is the primary data source for this region. Lead completeness scores will naturally be lower for Middle East leads — this is expected and accepted. Leads from this region receive a note: "Official registry data unavailable for this jurisdiction."

---

### Southeast Asia (Singapore, Malaysia, Indonesia)

| Source | What it gives | Type |
|---|---|---|
| ACRA BizFile+ API | Singapore company registration, directors | Official government API (paid) |
| OpenCorporates | Malaysia, Indonesia coverage | Aggregator API |
| Apollo.io | Company overview, person profile | Licensed commercial API |

---

## Four Real-World Scenarios

---

### Scenario 1: The Enterprise B2B Lead (Happy Path)

**Message received on WhatsApp:**
> "I am Aishekh Prasad from Inmobi lucknow i am the cto and I want to buy something"

**Channel gives automatically:** phone number +91-98XXXXXXXX

---

**Pre-Filter:** Message is 71 characters, contains meaningful words → passes.

**Message Parser (Haiku):**
```
name: "Aishekh Prasad"
company: "InMobi"
role: "CTO"
location_mentioned: "Lucknow"
intent_text: "I want to buy something"
business_ownership: false
```

**Free Signal Scorer:**
- Company name "InMobi" → +3 B2B
- Role "CTO" → +2 B2B
- Total: **+5 → B2B confirmed.** No identity API needed for classification.

**Jurisdiction:** `libphonenumber(+91-98XXXXXXXX)` → **India (IN)**

**Account Graph:** No prior InMobi contacts found. `account_engagement_signal: NONE`.

**Conversation Thread:** No open thread found. New lead.

**Company Cache:** "InMobi" + "IN" → cache miss. Continue.

**Company Disambiguator:** Apollo search "InMobi" + country India → one result, confidence 95%. InMobi Technologies Pvt Ltd. Proceed.

**Company Resolver:**
- Apollo.io → industry: Mobile Advertising/AdTech, size: 1001–5000 employees, founded: 2007, revenue estimate: $100M–$500M
- MCA21 API → directors list, CIN: U72200KA2007PTC043198, company type: Private Limited, incorporated: 2007-12-19
- GST Portal → trade name confirmed, GST status: Regular

Company profile written to cache. TTL: 30 days.

**Person Resolver:**
- Apollo person search "Aishekh Prasad" + "InMobi" → role: CTO, last updated: 4 months ago → `role_unverified: false` (within 6-month window)
- Phone cross-reference: Apollo phone for this person matches the WhatsApp number → `identity_verified: true`

**Location Reconciliation:**
- Apollo says InMobi HQ: Bangalore
- Message says: Lucknow
- **Decision:** `lead_location: Lucknow` | `company_hq: Bangalore` — correctly separated

**Consent Gate:** Tenant has DPDP consent configured. Proceed.

**Intent Gate:** `intent_specificity: very_low` + `fit_score: HIGH (estimated)`
→ Automated clarification sent via WhatsApp: *"Hi Aishekh, thanks for reaching out! To help you faster, could you tell us what you're looking to buy and roughly how many you need?"*
→ Lead status set to `awaiting_clarification`
→ Salesperson sees card: "Clarification pending — awaiting reply from lead"

**If Aishekh replies:** *"I need 500 licenses of your enterprise plan, budget around ₹25L, need it activated by June"*
→ Pipeline re-runs with both messages
→ Intent jumps from `very_low` to `very_high`
→ Score upgrades significantly

**Final Score (before clarification reply):**
```
score:  62
bucket: WARM
reasoning: CTO of a large established AdTech company — excellent fit.
           Intent is non-specific; score capped until clarification received.
lead_completeness: 0.72
identity_verified: true
```

**What the salesperson sees:** WARM card, clarification pending, do not contact manually.

---

### Scenario 2: The Small Business Owner (SMB Path)

**Message received on WhatsApp:**
> "I am Sunita Sharma, I run a small catering business in Lucknow and I want to order supplies in bulk"

**Channel gives:** phone number +91-97XXXXXXXX

---

**Pre-Filter:** Passes.

**Message Parser:**
```
name: "Sunita Sharma"
company: null   ← no company name stated
role: null
location_mentioned: "Lucknow"
intent_text: "want to order supplies in bulk"
business_ownership: true   ← "I run a small catering business"
```

**Free Signal Scorer:**
- No company name → 0
- No job title → 0
- Business ownership phrase "I run a small catering business" → **+3 B2B**
- "bulk order" → **+3 B2B**
- Total: **+6 → B2B confirmed**

Without the business ownership signals, this lead would have scored 0 and been classified as B2C. That would have been wrong — Sunita is a business buyer.

**Jurisdiction:** +91 → India (IN)

**Company Resolver:**
- Apollo.io search for "Sunita Sharma catering Lucknow" → **no record found** (small local business, not in Apollo's database)
- MCA21 search by approximate name → returns 200+ companies with "catering" in name across UP, no reliable match
- GST Portal → no GSTIN available (many small caterers are below GST threshold or unregistered)
- **Result:** Company not found in any source

**How the system handles this:** It does not fail. It records what it knows:
```
company_name:      "Sunita's Catering" (inferred from message)
company_verified:  false
company_size:      micro/small (inferred from "small" in message)
industry:          Catering / Food Services (inferred from message)
lead_completeness: 0.38   ← reflects the missing company data
```

**Intent Gate:** `intent_specificity: medium` (bulk order = clear buying intent, no quantity/budget yet) + `fit_score: MEDIUM`
→ No automated clarification triggered. Score with current data.

**Final Score:**
```
score:  44
bucket: COLD
reasoning: Verified business buyer with clear bulk purchase intent.
           Company details could not be verified — no formal registration found.
           Recommend qualifying: ask for business type and order size.
lead_completeness: 0.38
note: "Ask for GST number or business name in conversation to improve score"
```

**Key insight:** This lead is not cold because Sunita is unimportant. She's cold because the system doesn't have enough verified data. The note prompts the salesperson to ask the right qualifying questions. If Sunita provides her GST number, the pipeline re-runs, completeness jumps, score upgrades.

---

### Scenario 3: The Hinglish Message

**Message received on WhatsApp:**
> "bhai main inmobi se bol raha hu cto hu kuch lena tha"

*(Translation: "Bro I'm calling from InMobi, I'm the CTO, wanted to buy something")*

**Channel gives:** phone number +91-99XXXXXXXX

---

**Pre-Filter:** Passes. 52 characters, meaningful content.

**Message Parser (Haiku):** This is where the LLM earns its place. A regex-based parser would miss "inmobi se bol raha hu" entirely. Haiku, which is multilingual, reads the Hindi and extracts:
```
name: null   ← not mentioned
company: "InMobi"
role: "CTO"
location_mentioned: null
intent_text: "wanted to buy something"
language_detected: "hi"
```

Without Haiku, this message would have returned empty extraction → lead classified as noise → discarded. A real high-value lead lost.

**Rest of pipeline:** Continues identically to Scenario 1 once the structured data is extracted. The language of the original message does not matter after the parsing step.

**Note for the salesperson's card:** Response can be sent in Hindi if the tenant configures language preference matching.

---

### Scenario 4: International B2B Lead (UK)

**Message received on LinkedIn:**
> "Hi, I'm James Whitfield, CTO at Barclays. Reached out because we're evaluating enterprise vendors for our data platform. Can you share your pricing and technical specs?"

**Channel gives:** LinkedIn profile URL + phone if provided

---

**Pre-Filter:** Passes.

**Message Parser:**
```
name: "James Whitfield"
company: "Barclays"
role: "CTO"
location_mentioned: null
intent_text: "evaluating enterprise vendors, want pricing and technical specs"
business_ownership: false
```

**Free Signal Scorer:**
- Company name "Barclays" → +3 B2B
- Role "CTO" → +2 B2B
- Lead source: LinkedIn → +2 B2B
- Intent "evaluating vendors" → very explicit
- Total: **+7 → B2B confirmed**

**Jurisdiction:** LinkedIn does not give a phone number automatically. If no phone → use LinkedIn profile location or company HQ. Company "Barclays" → Apollo returns HQ: London, UK → **country: GB (United Kingdom)**

**Source Registry lookup for GB:**
```
Sources: [Apollo.io → Companies House API → OpenCorporates]
```

**Company Resolver:**
- Apollo.io → Barclays: Financial Services, 80,000+ employees, founded 1690, revenue: >$10B
- Companies House API → full filing history, directors, SIC code: 64190 (Banks), accounts filed

**Intent Gate:** `intent_specificity: HIGH` ("evaluating vendors, want pricing and specs" is specific)
→ No automated clarification. Score immediately.

**Final Score:**
```
score:  88
bucket: HOT
reasoning: CTO of a FTSE 100 financial institution actively evaluating vendors.
           Explicit vendor comparison intent with specific information request.
           High authority decision-maker. Immediate follow-up required.
lead_completeness: 0.91
identity_verified: true   ← LinkedIn profile confirmed
```

**What the salesperson sees:** HOT card, push notification sent, 24-hour SLA timer started.

---

## What Happens When the System Gets Feedback

Feedback from the salesperson closes two loops, not one.

**Loop 1 — Scoring calibration (existing):**
Thumbs up/down on the bucket rating feeds back to the Scoring Agent's calibration. If many HOT leads are not converting, bucket thresholds adjust.

**Loop 2 — Enrichment quality (new, from this architecture):**
- Salesperson marks "wrong company" → company cache entry invalidated, Apollo confidence flagged low for this record
- Salesperson marks "this person left the company" → person record flagged as stale, role_unverified set true retroactively
- Salesperson marks "company details incorrect" → triggers re-enrichment on next touch from this company

Without Loop 2, the system keeps serving wrong data confidently. With Loop 2, enrichment quality improves over time.

---

## What Changes for B2C Leads

For a B2C lead, Steps 7 and 8 (Company Resolver and Person Resolver) take a different path.

There is no company to look up. The enrichment focuses entirely on the person:

| Source | Region | What it gives |
|---|---|---|
| Truecaller for Business | India (primary) | Name, bio, occupation, location — very high coverage for India |
| People Data Labs (PDL) | Global | Phone → personal profile, professional background |
| Instagram Graph API | Global | Public account data if they messaged via Instagram |

B2C leads will always have lower `lead_completeness` than B2B leads. This is expected. The Scoring Agent is aware of this and does not penalize B2C leads unfairly — it evaluates them on the signals that are available.

---

## Phase 2 Improvements (Not MVP)

The following are real improvements identified during architecture review. They are deferred because the MVP can function without them, and they require more production data or more development time to do properly.

| Improvement | What it solves | When to build |
|---|---|---|
| Company disambiguation UI | Salesperson picks the right company from a short list when confidence is below 80% | After Month 1 — need to see how often it triggers |
| Feedback → enrichment quality loop | Wrong company / stale role flags invalidate cache | After Month 1 — need feedback volume |
| Account-level intelligence depth | Visualize which roles from a company have engaged, account-level intent score | Sprint 2 |
| Competitor detection | Flag leads from competitor companies | After Month 2 |
| Middle East official APIs | If UAE/Saudi release official APIs, add to registry | Ongoing monitoring |

---

## Open Questions

1. **Automated clarification timeout:** If the system sends a clarification message and gets no reply, how long should it wait before scoring with a completeness penalty? Suggested: 24 hours. `[TBD — team decision]`
2. **SMB qualification prompt:** What specific question should the system ask an SMB lead whose company cannot be found? "Can you share your GST number?" is effective for India but not global. `[TBD — per-tenant configuration]`
3. **Conversation threading scope:** Should re-scoring on clarification reply be automatic, or should the salesperson trigger it? `[TBD — UX decision]`
4. **Apollo vs PDL as global spine:** Apollo is stronger for B2B; PDL is stronger for B2C personal identity. If the tenant mix becomes predominantly B2C, revisit this choice. `[TBD — review after Month 1 tenant mix data]`

---

## Section 14 — How the Meta Integration Connects to This Pipeline

This section defines the exact handoff between the Meta webhook layer ([[analyses/meta-integration-implementation]]) and Pipeline 1 (this document). It answers: what format does the data arrive in, which steps does each channel type enter at, and where exactly does each external tool get called?

---

### 14.1 Two Entry Paths — DM Events vs Lead Ad Events

The pipeline does not have a single entry point. There are two, depending on how the lead reached the system:

```
DM Event (WhatsApp / Instagram / Facebook Messenger)
  → Webhook Worker produces NormalisedChannelEvent
  → Enters at Step 0 (Pre-Filter Gate)
  → Full pipeline runs, including Message Parser (Haiku)

Lead Ad Event (Facebook Lead Ads / Instagram Lead Ads)
  → Webhook Worker + Lead Retrieval Worker produce NormalisedChannelEvent
  → SKIPS Steps 0, 1, 2 (Pre-Filter, Message Parser, Free Signal Scorer)
  → Enters at Step 3 (Jurisdiction Classifier) with pre-structured fields
```

Lead Ads skip the first three steps because the form data already provides structured `name`, `email`, `phone`, `company_name`, and `job_title`. There is no raw message to filter or parse, and B2B/B2C classification can be determined directly from the presence or absence of `company_name` in the form response.

---

### 14.2 The NormalisedChannelEvent Schema

This is the exact data structure produced by the Meta webhook worker that enters Pipeline 1 at either entry point:

```json
{
  "event_type":          "dm" | "lead_ad",
  "channel":             "whatsapp" | "instagram" | "facebook",
  "tenant_id":           "t_abc123",
  "connection_id":       "conn_xyz456",
  "platform_event_id":   "wamid.HBgL... | m_toDnmD... | 123456789",
  "timestamp":           "2026-05-03T10:00:00Z",

  // DM event fields — present when event_type = "dm"
  "message_text":        "I am Aishekh Prasad from InMobi...",
  "sender_phone":        "+919876543210",     // WhatsApp only (E.164 format)
  "sender_wa_id":        "919876543210",      // WhatsApp only
  "sender_display_name": "Aishekh",           // WhatsApp only; self-reported, not identity-verified
  "sender_psid":         "123456789012345",   // Facebook Messenger only
  "sender_igsid":        "17841406455399901", // Instagram only

  // Lead Ad event fields — present when event_type = "lead_ad"
  "lead_form_fields": {
    "email":        "priya@example.com",
    "phone":        "+919876543210",
    "full_name":    "Priya Sharma",
    "company_name": "Acme Pvt Ltd",
    "job_title":    "Founder",
    "city":         "Mumbai"
  },
  "extra_fields": {
    "Which city are you from?": "Mumbai"
  },
  "ad_id":      "222222222",
  "form_id":    "987654321",
  "leadgen_id": "123456789"
}
```

**Key constraint:** `sender_phone` is always present for WhatsApp events. For Facebook and Instagram DM events, the sender's phone number is NOT in the payload — only the PSID (Facebook) or IGSID (Instagram). Phone-based enrichment tools (Truecaller, `libphonenumber`) do not apply to Facebook/Instagram DM leads unless the lead form or conversation explicitly provides a phone number.

---

### 14.3 Lead Ad Pre-Population at Pipeline Entry

When `event_type = "lead_ad"`, the following fields from `lead_form_fields` feed directly into the pipeline without parsing:

| Form field | Pipeline step it feeds | How |
|---|---|---|
| `phone` | Step 3 (Jurisdiction Classifier) | `libphonenumber(phone)` → `country_code` |
| `company_name` | Step 7 (Company Disambiguator) | Primary search key |
| `phone` or `email` | Step 9 (Person Resolver) | Apollo.io primary search key |
| `full_name` | Step 9 (Person Resolver) | Seeds Apollo name search |
| `job_title` | Step 9 output | Seeded directly; no lookup needed for role |
| `company_name` presence | B2B/B2C determination | `company_name` present → B2B; absent → B2C path |

For Lead Ad events, the Free Signal Scorer (Step 2) is replaced by this direct field check. The Message Parser (Step 1) is skipped entirely.

---

### 14.4 Instagram's Dual Role: Channel AND Enrichment Source

Instagram plays two distinct roles in this pipeline:

**Role 1 — Channel:** Instagram DMs and Lead Ads arrive via the Meta webhook (`object: "instagram"`). The NormalisedChannelEvent `channel = "instagram"` tells the pipeline that the lead originated from Instagram. This happens before Step 0.

**Role 2 — Enrichment source at Step 9 (Person Resolver):** When `channel = "instagram"` AND `sender_igsid` is present, the Instagram User Profile API is called before Apollo.io:

```
GET https://graph.instagram.com/v25.0/{sender_igsid}
   ?fields=name,username,profile_pic,follower_count,
           is_verified_user,is_user_follow_business,is_business_follow_user
   &access_token={instagram_user_access_token}
```

This returns the lead's username, display name, follower count, and verification status — before any Apollo.io lookup. For Instagram DM leads, this often resolves the person identity without a paid API call.

`follower_count` and `is_verified_user` are also signal inputs to the Scoring Agent: a verified account with 100k+ followers contacting a B2C fashion brand is a qualitatively different lead than an anonymous account with 50 followers.

---

### 14.5 Facebook Messenger Follow-Up Call at Step 9

When `channel = "facebook"` AND `sender_psid` is present, the Facebook sender profile call runs at the start of Step 9 (Person Resolver), before Apollo:

```
GET /{sender_psid}
   ?fields=name,first_name,last_name,profile_pic
   &access_token={page_access_token}
```

This seeds `full_name` for the Apollo.io person search. If the call returns null fields (strict privacy settings), Step 9 proceeds with Apollo using whatever name the lead provided in their message (extracted by the Message Parser at Step 1).

---

### 14.6 WhatsApp Identity Constraint

WhatsApp webhook payloads provide `sender_phone` (the `wa_id`) and optionally `sender_display_name` (the WhatsApp profile name — self-reported, unreliable as an identity field). No Instagram-style profile call exists.

At Step 9 (Person Resolver), WhatsApp leads use the phone number as the Apollo.io search key:
```
Apollo person search: phone_number = sender_phone
```

For India WhatsApp leads, Truecaller for Business is also called using the phone number — often returning a more reliable name than the WhatsApp display name.

`sender_display_name` is stored on the lead record but is not used as an identity input for enrichment or scoring.

---

### 14.7 Full API Call Map by Step

| Step | DM path trigger | Lead Ad path trigger | API called | Cost |
|---|---|---|---|---|
| Step 0 (Pre-Filter) | Every DM | Skipped | None — code logic | Free |
| Step 1 (Message Parser) | DM only | Skipped | Claude Haiku LLM | ~$0.001 |
| Step 2 (Signal Scorer) | DM only | Skipped; replaced by field check | None — code logic | Free |
| Step 3 (Jurisdiction) | Every event | Every event | `libphonenumber` (local lib) | Free |
| Step 4 (Account Graph) | Every event | Every event | PostgreSQL query | Free |
| Step 5 (Thread Check) | DM only | Skipped | PostgreSQL query | Free |
| Step 6 (Company Cache) | B2B events only | B2B events only | Redis / PostgreSQL | Free |
| Step 7 (Company Disambiguator) | Cache miss + B2B | Cache miss + B2B | Apollo.io API | ~$0.01–0.03 |
| Step 8 (Company Resolver) | After Disambiguator | After Disambiguator | See registry table below | Varies |
| Pre-Step 9 — Facebook sender | FB DM only | N/A | `GET /{psid}?fields=name` via Graph API | Free (page token) |
| Pre-Step 9 — Instagram sender | IG DM only | N/A | Instagram User Profile API `GET /v25.0/{igsid}` | Free (IG token) |
| Step 9 (Person Resolver) — WA/Lead Ad | WA DM + Lead Ad | Lead Ad | Apollo.io person search (phone or email key) | ~$0.01–0.03 |
| Step 9 (Person Resolver) — India B2C | India leads | India leads | Truecaller for Business (phone key) | Per-call |
| Step 9 (Person Resolver) — fallback | Any | Any | People Data Labs (PDL) | Per-call |
| Step 10 (Location Reconcile) | After Step 9 | After Step 9 | None — code logic against Step 8+9 data | Free |
| Step 11 (Consent Gate) | Every event | Every event | PostgreSQL (tenant policy table) | Free |
| Step 12 (Intent Gate) | Every event | Every event | Rule logic; may trigger channel send | Free |
| Step 13 (Scoring Agent) | After Step 12 | After Step 12 | Claude Sonnet — 1 call | ~$0.01–0.05 |

**Company Resolver API calls by jurisdiction (Step 8):**

| Country | Sources tried in order | Cost |
|---|---|---|
| India (IN) | Apollo.io → MCA21 API (free) → GST Portal API (free) → OpenCorporates | $0.01–0.03 |
| UK (GB) | Apollo.io → Companies House API (free) → OpenCorporates | $0.01–0.03 |
| US | Apollo.io → SEC EDGAR (free, public co. only) → OpenCorporates | $0.01–0.03 |
| EU | Apollo.io → VIES API (free) → OpenCorporates | $0.01–0.03 |
| Middle East | Apollo.io → OpenCorporates (limited) | $0.01–0.03 |
| SEA (SG) | Apollo.io → ACRA BizFile+ (paid) → OpenCorporates | $0.01–0.05 |

---

### 14.8 The Handoff Point — Where Does the Meta Layer End and This Pipeline Begin?

```
Meta Webhook POST arrives at /webhooks/meta
    ↓
HMAC validation (app secret, raw bytes)
    ↓
Enqueue raw payload
    ↓
Return HTTP 200
    ↓
[async] Webhook Router Worker:
    - reads payload["object"] → identifies surface
    - queries channel_connection by page_id / ig_account_id / phone_number_id → finds tenant
    - dispatches to surface-specific handler
    ↓
[For Lead Ads] Lead Retrieval Worker:
    - calls GET /{leadgen_id} on Graph API
    - normalises field_data via lead_form_field_map
    ↓
[For all events] NormalisedChannelEvent is constructed
    ↓
===== THIS IS THE BOUNDARY =====
NormalisedChannelEvent is written to the event_queue
Pipeline 1 is triggered with event_type + channel metadata
    ↓
Step 0 (DM path) or Step 3 (Lead Ad path) — Pipeline 1 begins
```

Everything above the boundary is the Meta integration layer ([[analyses/meta-integration-implementation]]). Everything at and below the boundary is this document. The NormalisedChannelEvent schema (Section 14.2) is the contract between the two layers. Neither layer should assume knowledge of the other's internals beyond this schema.

---

## Relationship to Other Documents

- [[analyses/lead-enrichment-architecture]] — Original enrichment architecture (India-specific provider stack). The registry-driven global approach in this document supersedes the hard-coded India provider list from that document. The signal separation principle, two-phase model, and NormalisedEvent schema in that document remain valid and are not changed.
- [[analyses/meta-integration-implementation]] — Defines how each Meta surface is connected (Facebook OAuth, Instagram OAuth, WhatsApp Embedded Signup), webhook routing implementation, and Lead Ads retrieval. Section 14 of this document defines the boundary between that layer and this pipeline.
- [[analyses/signal-detection-rule-spec]] — Defines what signals are extracted from the NormalisedCompanyProfile produced by this pipeline.
- [[analyses/orchestration-layer-spec]] — Defines the overall pipeline controller that runs the steps in this document.
- [[analyses/rating-agent-spec]] — Specifies what the Scoring Agent does with the enriched lead produced by this pipeline.
- [[analyses/channel-integration-layer]] — Original channel integration overview. The Meta-specific OAuth and webhook details in that document are superseded by [[analyses/meta-integration-implementation]]; the NormalisedEvent schema and token lifecycle patterns remain valid.
