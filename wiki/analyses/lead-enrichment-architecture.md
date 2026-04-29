---
type: analysis
question: "How does lead enrichment and investigation work end-to-end, and what providers are used for Indian businesses?"
date: 2026-04-30
tags: [enrichment, investigation, pipeline-1, normalised-event, providers, india, truecaller, gst, mca, justdial, indiamart, apollo, instagram, identity-graph, channel-integration, whatsapp, bsp, signal-separation]
sources_consulted:
  - "[[analyses/signal-detection-rule-spec]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[concepts/data-entity-model]]"
  - "[[analyses/channel-integration-layer]]"
status: COMPLETE — decisions locked for POC build
---

# Lead Enrichment and Investigation Architecture

**Question:** How does lead enrichment and investigation work end-to-end, and what providers are used for Indian businesses?
**Date:** 2026-04-30

---

## The Fundamental Separation (Read This First)

Three things must never be conflated:

| Step | What it does | What it uses | What it produces |
|---|---|---|---|
| **Signal creation** (Pipeline 2) | Defines what questions to ask about every lead | ICP + tenant persona ONLY — no lead data | Signal definitions with detection_rules |
| **Enrichment** (Pipeline 1, Stage 2a) | Collects data about this specific lead | External APIs, platform data, prior history | Populated NormalisedEvent |
| **Signal evaluation** (Pipeline 1, Stage 2b) | Answers each signal question using the lead's data | Signal definitions + NormalisedEvent | Signal values: 0.0–1.0 per signal |

**Signals never know about enrichment. Enrichment never knows about signals. Signal evaluation is the bridge.**

The Signal Agent in Pipeline 2 looks only at the ICP — "for a bike shop whose ideal customer is an active cycling enthusiast, what questions should we ask about every lead?" It produces signal definitions with no awareness of any specific lead.

Enrichment independently collects data about a specific lead — message content, location from Truecaller, Instagram bio from Graph API. It has no awareness of what signals exist.

Signal evaluation then runs each detection_rule against the NormalisedEvent:

```
cycling_lifestyle_fit.detection_rule  →  enriched_topic_affinity.cycling = 0.9
pricing_request.detection_rule        →  message_content: "bhai bike ka price kya hai"
geography_match.detection_rule        →  enriched_geography: "Pune, Tier-2"
```

The signal QUESTION was defined from the ICP. The signal ANSWER comes from the enriched lead. Produced independently, connected only at evaluation time.

---

## Two-Phase Enrichment Model

Enrichment happens in two phases with different timing:

```
Lead arrives
    ↓
PHASE 1 — Synchronous enrichment (runs before initial score)
  Tier 1 + Tier 2 only
  Must complete before Pipeline 1 produces a score
  Target: under 1 second total
    ↓
Initial score assigned → lead appears in salesperson dashboard
    ↓
PHASE 2 — Investigation (async, runs on every lead after capture)
  Deep social + business enrichment
  Runs in background while salesperson reads the initial card
  Score updates automatically when investigation completes
  Target: 10–60 seconds
```

The salesperson always gets a fast initial bucket. The richer profile populates while they're reading.

---

## Tier 1 — First-Party Interaction Data

Always available. No external calls. Zero cost.

```
├─ The message / form response / ad click the lead sent
├─ Their history with this tenant (prior touchpoints in DB)
└─ Website behaviour on the tenant's own properties

Populates: message_content, form_response, page_type,
           source_type, utm_*, lead_history
Cost: $0  |  Latency: ~0ms
```

---

## Tier 2 — Identity Resolution (Synchronous)

Always attempted. Runs before the initial score.

```
├─ Phone verification (Truecaller for Business)
│    → verified name, city, state, carrier, spam score
│    → whether it's a personal or business number
│    → profile bio text (many Indians write lifestyle info here)
└─ Google Places API (phone → business lookup)
     → does this number belong to a registered business?
     → business category, Google rating, years listed

Populates: enriched_geography, enriched_truecaller_bio,
           enriched_business_flag, enriched_google_business_category
Cost: ~$0.002–$0.02/lead  |  Latency: 200–500ms
```

**PDL (People Data Labs) is on hold.** Coverage for Indian B2C consumers is ~20–30% — not reliable enough to depend on for handle discovery. Indian government and directory sources give more reliable signal for the same leads.

---

## Phase 2 — Investigation Layer (Async)

Runs on every lead after capture. B2B and B2C paths are different because they need different data.

### B2B Investigation Path

```
Triggered when: enriched_business_flag = true OR source is LinkedIn Lead Ad OR tenant type is B2B

Step 1 (parallel):
  GST Verification API
    input:  GSTIN (if captured) OR business name + state
    output: GST registration status, business category,
            turnover slab (e.g. "1Cr–5Cr"), registration date
    cost:   free  |  time: ~200ms

  MCA API (Ministry of Corporate Affairs)
    input:  company name OR director name
    output: company type (Pvt Ltd / LLP / sole proprietor),
            paid-up capital, incorporation date, active status
    cost:   free  |  time: ~300ms

Step 2 (parallel):
  JustDial lookup
    input:  phone number OR business name + city
    output: business category, customer reviews,
            years listed, verified badge
    cost:   scrape  |  time: ~500ms

  IndiaMART lookup
    input:  phone number OR business name
    output: product categories traded, buyer/seller status,
            trust seal level
    cost:   scrape  |  time: ~500ms

Step 3:
  Apollo.io (for corporate employees — not SMB owners)
    input:  name + company name
    output: job title, seniority, department, company size
    cost:   ~$0.05/call  |  time: ~300ms

Populates: enriched_gst_registered, enriched_gst_turnover_slab,
           enriched_company_type, enriched_paid_up_capital,
           enriched_justdial_category, enriched_indiamart_listed,
           enriched_job_title, enriched_company_size, enriched_industry
```

**GST turnover slab is the most powerful B2B qualification signal.** A business with ₹1Cr–5Cr turnover has very different budget and buying behaviour than a ₹5L/year sole proprietor. This data is free, official, and completely reliable.

### B2C Investigation Path

```
Triggered when: enriched_business_flag = false AND tenant type is B2C

Step 1:
  Instagram Graph API (if Instagram handle available)
    input:  username + tenant Meta token
    output: bio text, follower count, following count,
            post count, highlights (often public even on private accounts)
    cost:   free  |  time: ~150ms

Step 2 (if account is public):
  Apify Instagram Post Scraper
    input:  username
    output: recent post captions, hashtags, tagged brands,
            location tags, engagement rate
    cost:   ~$0.01/profile  |  time: ~2–5s

Step 3:
  YouTube Data API (if YouTube channel can be found by name)
    input:  lead name + city
    output: channel topics, subscription categories
    cost:   free (quota-based)  |  time: ~300ms

Populates: enriched_bio_text, enriched_topic_affinity,
           enriched_community_signals, enriched_interest_categories,
           enriched_social_activity_level
```

**Why Truecaller bio matters here:** Many Indian consumers write lifestyle-indicating bios in Truecaller — "Yoga teacher | Pune", "Gym owner | Mumbai", "MTB cyclist". This is free and already captured in Tier 2 but feeds directly into B2C scoring.

---

## Why This Stack Is Built for India

The Western-centric scraping approach (LinkedIn post scraping, Facebook profile scraping) fails for Indian leads because:

1. Most Indian consumer Facebook profiles are private — scrapers return nothing
2. LinkedIn post content scraping is extremely unreliable — LinkedIn actively blocks bots
3. PDL covers ~20–30% of Indian B2C leads — too sparse to depend on

**The Indian internet has a different identity layer.** Phone number is the primary identifier — linked to Aadhaar, UPI, bank accounts, WhatsApp. This is why:

- **Truecaller** with 250M+ Indian users is more authoritative than any Western data provider for identity
- **GST and MCA** are official, free, and complete for any registered Indian business — no Western equivalent exists
- **JustDial and IndiaMART** cover Indian SMBs that Apollo and PDL have never indexed

The provider decisions follow from this: use what's authoritative for India, not what's designed for US/EU markets.

---

## Provider Reliability Comparison

| Source | Reliability | India Coverage | Cost | Notes |
|---|---|---|---|---|
| Truecaller API | Very high | 250M+ Indian users | ~$0.001/call | Most reliable Indian identity source |
| Google Places API | Very high | Massive India coverage | $0.017/call | Reliable for business phone lookups |
| GST API | 100% | All GST-registered businesses | Free | Official government source |
| MCA API | 100% | All registered companies | Free | Official government source |
| JustDial | High | Indian SMBs specifically | Scrape | India-specific, not in Western DBs |
| IndiaMART | High | Indian B2B traders/manufacturers | Scrape | Active buyers/sellers indexed |
| Apollo.io | Medium-high | Urban Indian professionals | ~$0.05/call | B2B corporate employees only |
| Instagram Graph API | High | Instagram DM leads | Free | Official, stable |
| Apify Instagram | Medium | Public accounts only | ~$0.01/profile | Fails on private accounts |
| YouTube Data API | Medium | If channel found by name | Free (quota) | Identity link is the challenge |
| LinkedIn post scraping | Low | Unreliable | Unpredictable | LinkedIn actively blocks — do not depend on |
| Facebook profile scraping | Very low | Mostly private | Unpredictable | Post-Cambridge Analytica, data is gone |
| WhatsApp investigation | None | Closed system | — | Nothing to scrape |

---

## Source Channel Effects on Enrichment

The channel a lead arrived from determines what identity data is immediately available:

| Channel | Free identity data | Investigation starting point |
|---|---|---|
| Instagram DM | Instagram handle (in event payload) | Skip handle discovery → straight to Graph API + Apify |
| WhatsApp | Phone + display name | Truecaller → Google Places → GST/MCA/JustDial/IndiaMART |
| LinkedIn Lead Ad | Full LinkedIn profile + form fields | Already have everything; Apollo optional for company enrichment |
| Facebook Messenger | PSID → name only | Thinnest path; investigation adds little |
| Website form | Name + email + page behaviour | Email → Apollo (B2B); Instagram handle search by name |
| Meta Lead Ad | Form fields + UTM data | Depends on what the form captured |

---

## Non-Text Message Types

Not every message is text. These types carry additional signal:

| Type | What we receive | Signal value |
|---|---|---|
| Text | Full message body | Primary signal source |
| Image | Media URL | Store URL; signals limited without vision processing |
| Voice note | Audio URL | Whisper transcription — deferred to post-MVP |
| **Story reply (Instagram)** | Their reply text + story reference | Very strong — engaged with specific content |
| **Product catalogue tap (WhatsApp)** | Product ID selected | Highest intent — near-purchase decision |
| Button click (WhatsApp template) | Button label clicked | Strong intent — e.g. "Yes, I'm interested" |

The `NormalisedEvent` handles this via `message_type` and companion fields:

```python
message_type: "text" | "image" | "audio" | "story_reply" |
              "product_tap" | "button_click"
message_content: str | None
message_media_url: str | None
story_reference_id: str | None
product_id_selected: str | None
```

---

## The Internal Identity Graph — Caching Layer

Sits above all external provider calls. Checked first on every lead arrival, written to after every successful investigation.

```
Lead arrives with phone +91XXXXXXXXXX
        ↓
Check identity graph:
  SELECT * FROM identity_graph
  WHERE phone = '+91XXXXXXXXXX'
        ↓
  HIT → populate NormalisedEvent from cached profile
         skip all external API calls → ~0ms, $0
        ↓
  MISS → run Tier 2 + investigation
         on completion: write result to identity_graph
         → next appearance of this person = instant cache hit
```

The identity graph cross-links identifiers across channels:

```
Run 1:  WhatsApp → phone linked to name + city + Truecaller bio
Run 2:  Same person DMs Instagram → phone linked to IGSID + username
Run 3:  Same person fills website form → phone linked to email

Identity graph entry:
  phone:                    +91XXXXXXXXXX
  name:                     Anishekh Prasad
  city:                     Pune
  truecaller_bio:           "MTB rider | Pune"
  instagram_handle:         @anishekh_bikes
  instagram_igsid:          1234567890
  topic_affinity:           {cycling: 0.9}
  enrichment_tier_reached:  3
  last_seen:                2026-04-30
  seen_via:                 [whatsapp, instagram_dm]
```

---

## NormalisedEvent Field Expansion

Full set of enrichment fields on NormalisedEvent after all tiers and investigation:

```python
# Tier 1 — always present
message_content: str | None
form_response: dict | None
page_type: str | None
source_type: str
utm_source: str | None

# Tier 2 — identity resolution
enriched_geography: str | None          # "Pune, Maharashtra"
enriched_truecaller_bio: str | None     # Truecaller profile bio/status
enriched_business_flag: bool            # personal vs business number
enriched_google_business_category: str | None

# B2B Investigation fields
enriched_gst_registered: bool | None
enriched_gst_turnover_slab: str | None  # "40L–1Cr", "1Cr–5Cr", etc.
enriched_company_type: str | None       # "pvt_ltd" | "llp" | "sole_proprietor"
enriched_paid_up_capital: int | None    # in INR
enriched_justdial_category: str | None
enriched_indiamart_listed: bool | None
enriched_job_title: str | None          # Apollo — corporate employees
enriched_company_size: int | None
enriched_industry: str | None

# B2C Investigation fields
enriched_instagram_handle: str | None
enriched_linkedin_url: str | None
enriched_topic_affinity: dict[str, float] | None  # {"cycling": 0.9, "fitness": 0.6}
enriched_bio_text: str | None
enriched_community_signals: list[str] | None       # hashtags, group names
enriched_interest_categories: list[str] | None     # ["cycling", "outdoor_sports"]
enriched_social_activity_level: float | None       # 0.0–1.0
```

All fields follow the same null convention. Extractors must return `detected: false, value: 0.0` on null input — graceful degradation, not an error.

---

## New Extractor Types Required

Three B2C extractor types needed for social behavioral signals. Three B2B extractor types needed for Indian government data. All must be added to [[analyses/signal-detection-rule-spec]] and to the Persona Agent Step 3 vocabulary.

### B2C Extractor Types

| Type | Dimension | What it does | Key params |
|---|---|---|---|
| `topic_affinity_match` | Fit, Behaviour | Checks `enriched_topic_affinity[topic]` against threshold | `topic: str`, `min_affinity: float` |
| `interest_category_match` | Fit | Checks `enriched_interest_categories` against target list | `categories: list[str]`, `match_mode: any/all` |
| `bio_keyword_match` | Fit, Behaviour | Keyword search on `enriched_bio_text` or `enriched_truecaller_bio` | `keywords: list[str]`, `match_mode`, `threshold` |

### B2B Extractor Types

| Type | Dimension | What it does | Key params |
|---|---|---|---|
| `gst_turnover_threshold` | Fit | Checks if GST turnover slab meets minimum threshold | `min_slab: str` |
| `company_type_match` | Fit | Checks company registration type | `allowed_types: list[str]` |
| `business_directory_presence` | Fit | Checks JustDial/IndiaMART listing status | `source: "justdial" \| "indiamart"` |

---

## enrichment_tier_reached Field

The `lead_enrichment` entity carries:

```
enrichment_tier_reached: 1 | 2 | 3
investigation_completed: bool
investigation_completed_at: timestamp | None
```

`investigation_completed` separates the case where investigation ran and found nothing from where it hasn't run yet. Feeds `lead_completeness` calculation and diagnostic monitoring.

---

## B2C vs B2B Enrichment Strategy

| Tenant type | Most valuable investigation sources | Decisive fields | What separates good leads |
|---|---|---|---|
| B2B (e.g. Gamoft) | GST, MCA, JustDial, IndiaMART, Apollo | enriched_gst_turnover_slab, enriched_company_type, enriched_job_title | Budget signal (turnover), decision-maker status, business legitimacy |
| B2C (e.g. Urvee Organics) | Truecaller bio, Instagram Graph API, Apify public posts | enriched_topic_affinity, enriched_bio_text, enriched_community_signals | Lifestyle fit — enthusiast vs casual inquiry |

For B2C, whether someone is a doctor or a teacher is irrelevant — both buy organic products. What separates a committed health-conscious buyer from a one-time price-checker is the social and lifestyle signal layer.

For B2B, what separates a qualified prospect from a tire-kicker is business legitimacy and budget — exactly what GST turnover slab and MCA data reveal.

---

## How Enrichment Depth Affects Scoring Accuracy

```
Anishekh messages: "bhai bike ka price kya hai" via WhatsApp

Tier 1 only (initial score, instant):
  pricing_request:        1.0
  geography_match:        0.0   (no location data yet)
  cycling_lifestyle_fit:  0.0   (no social data yet)
  lead_completeness:      ~0.25 → needs_review = true
  → WARM at best

Tier 1 + Tier 2 (still synchronous, <1s):
  pricing_request:        1.0
  geography_match:        1.0   (Pune confirmed via Truecaller)
  cycling_lifestyle_fit:  0.3   (Truecaller bio: "MTB rider")
  lead_completeness:      ~0.50
  → WARM

After investigation completes (async, ~10–30s):
  pricing_request:        1.0
  geography_match:        1.0
  cycling_lifestyle_fit:  0.9   (Instagram: posts bikes 3x/week)
  bio_keyword_match:      1.0   ("MTB rider" in bio)
  community_depth:        0.85  (follows 40 bike brand accounts)
  lead_completeness:      ~0.82 → auto-route, no review needed
  → HOT — score updated, salesperson notified
```

---

## WhatsApp Connection Options

Two paths supported. Both produce identical `NormalisedEvent` output via the adapter pattern.

**Path A — Direct WABA**
- Tenant connects via GamoftX Meta App OAuth
- Messages arrive via Meta Cloud API webhook
- Webhook routed to tenant by `phone_number_id` in payload
- `channel_connection.auth_method = direct_waba`

**Path B — BSP Connector**
- Tenant already uses Interakt / WATI / AiSensy
- They paste their BSP API key into our onboarding
- BSP fires to tenant-specific URL: `/webhooks/{bsp_name}/{tenant_id}`
- `channel_connection.auth_method = interakt | wati | aisensy`

Tenant onboarding presents both options. Regular WhatsApp Business app has no programmatic API — tenants must migrate to WABA or sign up with a BSP.

---

## Cost Model

```
Per-lead cost at steady state (B2C WhatsApp lead):

  Tier 2:
    Truecaller:         $0.001  (always)
    Google Places API:  $0.017  (always)

  Investigation (B2C):
    Instagram Graph API: $0.00  (free)
    Apify Instagram:     $0.01  (public accounts only, ~20–30% of leads)

  Investigation (B2B):
    GST API:            $0.00  (free)
    MCA API:            $0.00  (free)
    JustDial scrape:    ~$0.005
    Apollo.io:          $0.05  (corporate employees only)

B2C lead, no public social profile:  ~$0.02/lead
B2C lead, public Instagram profile:  ~$0.03/lead
B2B lead, full investigation:        ~$0.08/lead

At 300 leads/day, mixed B2C/B2B:
  ~$6–9/day → ~$180–270/month

As identity graph fills (Month 3+):
  40% cache hit rate → drops to ~$110–160/month
  60% cache hit rate → drops to ~$70–110/month
```

---

## Open Items

- Define exact formula for `lead_completeness` given `enrichment_tier_reached`, `investigation_completed`, and null signal count
- Confirm Instagram Graph API biography field availability for personal (non-creator) accounts
- Add 6 new extractor types to [[analyses/signal-detection-rule-spec]] and update Persona Agent Step 3 vocabulary
- Add `identity_graph` as a formal entity to [[concepts/data-entity-model]] Group A
- Add `channel_connection` entity to [[concepts/data-entity-model]] Group A
- Add `enrichment_tier_reached` and `investigation_completed` fields to `lead_enrichment` entity
- Define cache TTL policy for identity graph entries (topic_affinity especially can go stale)
- JustDial and IndiaMART: confirm whether API access exists or scraping is the only path
- YouTube identity link: confirm practical path from lead name + city to YouTube channel
- Urvee Organics WhatsApp traffic nature (organic vs campaign) affects investigation volume estimate
