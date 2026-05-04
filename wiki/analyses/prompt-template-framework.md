---
type: analysis
question: "What is the standard prompt template framework for all LLM interactions in the Lead Intelligence Engine?"
date: 2026-05-04
tags: [prompt-engineering, llm, rating-agent, persona-agent, message-parser, template, b2b, sme, scoring, framework]
sources_consulted:
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[concepts/intelligence-layer]]"
  - "[[concepts/signal-types]]"
  - "[[concepts/persona-layer]]"
  - "[[concepts/confidence-first-class]]"
status: COMPLETE
---

# Prompt Template Framework

**Question:** What is the standard prompt template framework for all LLM interactions?
**Date:** 2026-05-04

---

## Answer / Finding

---

## 1. What Is a Prompt Template and Why Does It Need a Standard?

Every time this system asks an AI model to make a decision — whether scoring a lead, defining an ideal customer profile, or extracting meaning from a WhatsApp message — it sends a carefully structured block of text to the model. That block of text is the **prompt**.

Without a standard structure, every prompt looks different. That makes the system harder to maintain, harder to debug, and more expensive to run. When a score is wrong, you cannot easily tell whether the problem was in the instructions, the business context, or the lead data — because they were all mixed together in an unstructured way.

This framework defines a standard four-section structure that all prompts in this system follow. The sections are:

1. **SYSTEM** — what role the AI is playing and what rules it must follow
2. **CONTEXT** — the business-specific information the AI needs to do its job
3. **TASK** — the specific work to do right now (e.g., score this particular lead)
4. **OUTPUT FORMAT** — the exact structure the AI must return

This structure applies to every LLM call in the system, regardless of which model is used or which step in the pipeline is running.

---

## 2. The Four-Section Model

### 2.1 SYSTEM Section

**What it contains:**
The SYSTEM section tells the AI who it is and what its job is. It defines the role (e.g., "you are a lead scoring agent"), the scoring dimensions and what each one measures, the general rules the AI must follow (e.g., "do not hallucinate signal values"), and any constraints on how it should behave when data is missing.

**Key rules for this section:**
- Write it as a clear, direct role assignment: "You are a [role] for [business type]. Your job is to [task]."
- List all the things the AI must and must not do. These rules apply to every lead, not just specific ones.
- Include the scoring rubric here: dimension names, weights, and what each dimension measures.
- Include instructions for handling missing data: "If a signal value is `not_detected`, treat it as absent. Do not assume a positive value."

**Where it lives in the actual API call:**
The SYSTEM section goes into the **system message** of the API call (the `system` field in Anthropic's API). This is separate from the conversation turn — it sets the persistent context for the entire interaction.

---

### 2.2 CONTEXT Section

**What it contains:**
The CONTEXT section provides the business-specific configuration that makes this prompt work for *this particular tenant*. It includes:

- The tenant's business persona (what kind of company they are, who their customers are, what they sell)
- The Ideal Customer Profile (ICP) — a detailed description of the best kind of lead for this business, including disqualifying signals
- The signal definitions and their weights — the specific questions the system uses to evaluate leads, grouped by scoring dimension

**Key rules for this section:**
- This section is produced by the Persona Agent during onboarding. It does not change for every lead — only when the tenant updates their business configuration.
- Keep it specific. Vague context ("we are a B2B company") is less useful than specific context ("our best customers are Series A–C SaaS companies with 50–500 employees and a dedicated sales team").
- Include explicit disqualifying profiles so the AI understands who to exclude.

**Where it lives in the actual API call:**
The CONTEXT section also goes into the **system message**. It is appended after the SYSTEM section in the same system message block.

---

### 2.3 TASK Section

**What it contains:**
The TASK section is the only part of the prompt that changes for every lead. It contains:

- The **prompt variant** label (one of: `new`, `returning`, `rescore`) — see Section 4 for what each means
- The lead's contact and company information (name, phone, company, role, geography, source channel)
- The **data completeness score** (a number from 0.0 to 1.0 representing how complete this lead's data is — e.g., 0.87 means 87% of expected fields were filled)
- The **signal values** — one line per signal, showing what the system actually detected for this lead. Values can be `true`, `false`, a number, a category label (like `fast` or `slow`), or `not_detected` if the signal could not be determined.

For the `returning` variant: the previous score, bucket, and key touchpoints are also included here.
For the `rescore` variant: the previous score and the salesperson's feedback reason are included here.

**Key rules for this section:**
- Every signal defined for this tenant must appear here, even if its value is `not_detected`. Never leave a signal slot blank.
- The data completeness score must always be present. It tells the AI how much to trust its own reasoning — and tells the system when to route the lead for human review.
- The variant label must always be on the first line of this section.

**Where it lives in the actual API call:**
The TASK section goes into the **user message** of the API call — the first (and only) human turn in the conversation. This is the per-lead variable content.

---

### 2.4 OUTPUT FORMAT Section

**What it contains:**
The OUTPUT FORMAT section tells the AI exactly what to return and in what structure. For the Rating Agent (lead scoring), this is a JSON object with specific fields and types. This section includes:

- The full JSON schema with field names, types, and descriptions
- Strict instructions: "Return a single valid JSON object. No other text. No markdown."
- Guidance on specific fields (e.g., "return the data completeness value unchanged from what you received")

**Key rules for this section:**
- The output format must be machine-readable. Always ask for JSON.
- List every field the AI should return. Do not ask for fields the system will add itself (schema_version, prompt_version, model — those are added by the Output Schema Layer after the AI responds).
- Repeat the most important constraint here: "No explanation outside the JSON."

**Where it lives in the actual API call:**
The OUTPUT FORMAT section is the final part of the **system message**. Putting it at the end of the system message means it is the last instruction the AI reads before processing the user message.

---

## 3. The Static vs Variable Boundary

This is the most important architectural rule in the framework.

**The rule:** Everything in the system message (SYSTEM + CONTEXT + OUTPUT FORMAT) must be stable per tenant per prompt version. Only the user message (TASK) changes per lead.

**Why this matters — LLM provider caching:**
AI model providers like Anthropic cache the beginning of a prompt if it does not change between calls. This is called **prompt prefix caching**. For a batch of 50 leads from the same tenant, the system message (which contains the role, business context, ICP, signal definitions, and output format) is identical for all 50 leads. The provider caches it after the first call. Calls 2 through 50 reuse the cache — they are faster and cost fewer tokens.

If business context drifts into the user message, or if the user message contains anything from the system message, the cache breaks. Every call becomes a fresh, full-token call. This turns a 50% cost saving into zero.

**Visual separation:**

```
┌────────────────────────────────────────────────────────┐
│               SYSTEM MESSAGE (static per tenant)        │
│                                                        │
│  [SYSTEM]      Role, rules, scoring rubric             │
│  [CONTEXT]     Business persona, ICP, signal weights   │
│  [OUTPUT FMT]  JSON schema, field definitions          │
│                                                        │
│  ← Cached by LLM provider after first call per tenant  │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│               USER MESSAGE (per lead, variable)         │
│                                                        │
│  [TASK]  Variant, lead data, signal values,            │
│          data completeness score                        │
│                                                        │
│  ← Changes for every lead — never cached               │
└────────────────────────────────────────────────────────┘
```

**What triggers a new system message version?**
The system message version (tracked as `prompt_version` in the data layer) increments when:
- The tenant's business persona changes (Persona Agent re-runs)
- A new signal is added or removed
- Scoring weights are adjusted
- The scoring rules are updated

The version is recorded in the lineage log for every score, so you can always answer: "which prompt version was active when this lead was scored?"

---

## 4. How Prompt Variants Modify the TASK Section

The Rating Agent supports three prompt variants. The variant label appears at the top of the TASK section (user message). The system message never changes between variants — only the user message does.

| Variant | When used | What is added to the TASK section |
|---|---|---|
| `new` | First time this lead is being scored | Nothing extra. Only the current lead data and signal values. |
| `returning` | Lead was scored before and has come back with new activity | The previous score, previous bucket, and a summary of interaction history since the last score. The AI focuses on what has changed. |
| `rescore` | A salesperson has flagged this lead for re-evaluation | The previous score, previous bucket, and the salesperson's feedback reason (e.g., "lead confirmed budget, revisit score"). The AI re-evaluates with this new information in mind. |

**For the samples in this document:** Both samples use the `new` variant for simplicity. The framework applies to all three variants.

---

## 5. Framework Coverage — Which LLM Calls Use This Framework

The Lead Intelligence Engine makes five categories of LLM calls. All five follow the four-section framework, but the content of each section differs by call type.

| LLM Call | Model | SYSTEM | CONTEXT | TASK | OUTPUT FORMAT |
|---|---|---|---|---|---|
| **Rating Agent** (scoring) | Sonnet | Role: lead scorer. Rules, rubric | Tenant persona, ICP, signal definitions | Lead data + signal values + completeness | ScoringOutput JSON schema |
| **Message Parser** (extract from raw message) | Haiku | Role: message extractor. Multilingual rules | No tenant-specific context needed | Raw message text | Structured fields JSON (name, intent, company, etc.) |
| **Persona Agent Step 1** (business persona) | Sonnet | Role: business analyst. Persona creation rules | None (this step creates the context) | Tenant's business description | PersonaObject JSON schema |
| **Persona Agent Step 2** (ICP definition) | Sonnet | Role: ICP analyst. ICP creation rules | PersonaObject from Step 1 | Same tenant description + Step 1 output | IcpDefinition JSON schema |
| **Persona Agent Step 3** (signal definitions) | Sonnet | Role: signal designer. Signal rules + extractor vocabulary | Persona + ICP from Steps 1 & 2 | Business type + dimensions to cover | signal[] JSON schema |

**Scope of samples in this document:** Both samples (Section 6 and Section 7) are for the **Rating Agent** (lead scoring). This is the most frequent and most critical LLM call — it runs once per lead, for every lead, for every tenant. The Message Parser and Persona Agent prompts follow the same framework but are not shown here.

---

## 6. Sample Prompt 1 — B2B Lead Scoring (Enterprise Lead, Clear Signals)

### Setup

**Tenant:** Gamoft — a B2B SaaS company that sells the Lead Intelligence Engine platform to other businesses.
**Scenario:** A CTO at a funded SaaS startup has messaged on WhatsApp asking for a demo and pricing. The lead has engaged multiple times, responded quickly, and stated a clear timeline. Data completeness is high at 87%.
**Variant:** `new` (first time this lead is being scored)

### System Message

```
[SYSTEM]
You are a lead scoring agent for a B2B SaaS company. Your job is to read the provided
lead data, evaluate the lead across five scoring dimensions, and return a structured
score as a JSON object.

You are assessing inbound leads who have contacted the business through digital
channels (WhatsApp, Instagram, LinkedIn). Your score tells the sales team how
much priority to give this lead and what action to take next.

SCORING DIMENSIONS AND WEIGHTS
Evaluate the lead across exactly these five dimensions. Each dimension has a
maximum score equal to its weight as a percentage:

  Dimension    Weight   Max Score   What it measures
  ---------    ------   ---------   ----------------
  Fit           25%        25       How closely does this lead match the ideal
                                    customer profile (ICP)? Industry, company size,
                                    role, and serviceability.

  Intent        25%        25       How strongly has the lead expressed a desire
                                    to buy? Price requests, demo requests, urgency
                                    language, timeline statements.

  Engagement    20%        20       How actively has the lead engaged? Response
                                    speed, number of visits/messages, use of
                                    multiple channels, unprompted follow-ups.

  Behaviour     20%        20       What does the lead's past behaviour suggest
                                    about readiness? Prior purchases, referral
                                    type, content engagement, form completion.

  Context       10%        10       Do external factors support or weaken the
                                    lead? Geography tier, account growth signals,
                                    seasonal relevance.

The total score (0–100) is the sum of all five dimension scores.

BUCKETS
Assign a bucket based on total score:
  HOT   = 80–100  →  Contact within 24 hours
  WARM  = 55–79   →  Contact within 2–3 days
  COLD  = 0–54    →  Weekly nurture or archive

Assign the bucket that matches your total score. The system will verify
your bucket against the score and the tenant's threshold settings.

RULES — THESE APPLY TO EVERY LEAD
1. Only use the signal values provided in the TASK section. Never infer
   a signal value from the lead's name, location, or channel.
2. If a signal value is "not_detected", treat it as absent. Do not assume
   it is positive or negative. Do not penalise the lead for a missing signal
   unless the signal's absence is itself meaningful (e.g., no response to
   a follow-up is different from simply not having been asked yet).
3. Your reasoning must identify the two or three most important signals that
   drove the score — both signals that raised the score and any that lowered it.
4. Your recommended_action must be one sentence, specific to what a salesperson
   can do right now (e.g., "Call today to confirm demo timing and send pricing deck").
5. Never collapse sub_scores. Always return all five dimensions.
6. Return the data completeness value exactly as provided. Do not change it.

[CONTEXT]
ABOUT THIS BUSINESS (Gamoft)
Gamoft builds and sells the Lead Intelligence Engine — an AI-powered lead
management platform for sales teams. The platform helps B2B companies
automatically qualify, score, and prioritise inbound leads from WhatsApp,
Instagram, Facebook, and LinkedIn.

IDEAL CUSTOMER PROFILE (ICP)
Gamoft's ideal customer is a growing B2B company (Series A to Series C stage)
with 20–500 employees, an active inbound sales motion, and a dedicated sales
team of 2–20 people. They are based in India (Tier 1 or Tier 2 cities),
operate in the technology, SaaS, or professional services sector, and experience
high volumes of unqualified inbound leads from digital channels.

Decision-makers are typically CTOs, Heads of Sales, VP Sales, or Business Owners.
The biggest buying trigger is lead volume pain — when manually triaging WhatsApp
or Instagram DMs becomes a bottleneck for the sales team.

DISQUALIFYING PROFILES (exclude or penalise heavily)
- Students or recent graduates looking for internships or jobs
- Freelancers or solo operators with no sales team
- Companies in highly regulated industries that cannot connect social channels
- Resellers asking for white-labelled pricing (not direct customers)

SIGNAL WEIGHTS WITHIN EACH DIMENSION
  Fit dimension (max 25):
    industry_match          weight 0.35  (highest — industry fit is a hard prerequisite)
    role_relevance          weight 0.30  (decision-maker or influencer?)
    company_size_fit        weight 0.20  (does company size match the ICP range?)
    serviceability          weight 0.15  (can we actually serve this lead's geography?)

  Intent dimension (max 25):
    pricing_request         weight 0.30  (asked for pricing or a quote)
    demo_requested          weight 0.25  (asked to see the product)
    urgency_language        weight 0.20  (language signals time pressure)
    timeline_stated         weight 0.15  (gave a specific timeframe for decision)
    budget_mentioned        weight 0.10  (mentioned budget or approval process)

  Engagement dimension (max 20):
    response_speed          weight 0.25  (how fast did they reply when contacted?)
    revisit_count           weight 0.20  (how many separate interactions so far?)
    channel_diversity       weight 0.20  (contacted on one channel or multiple?)
    conversation_depth      weight 0.20  (shallow ping or substantive exchange?)
    follow_up_initiated     weight 0.15  (did the lead send an unprompted follow-up?)

  Behaviour dimension (max 20):
    prior_customer          weight 0.30  (have they bought from us before?)
    referral_source         weight 0.25  (referred by a customer vs cold inbound?)
    content_engagement      weight 0.25  (viewed pricing page, case studies, etc.)
    form_completion         weight 0.20  (completed a contact or demo request form?)

  Context dimension (max 10):
    geography_tier          weight 0.40  (Tier 1 city = strongest; Tier 3 = weakest)
    account_growth_signal   weight 0.35  (company recently funded, hiring, expanding?)
    seasonal_relevance      weight 0.25  (does seasonality favour a purchase now?)

[OUTPUT FORMAT]
Return a single valid JSON object. No other text before or after the JSON.
No markdown code blocks. No explanation outside the JSON structure.

JSON schema:
{
  "score": <integer 0–100>,
  "bucket": <"hot" | "warm" | "cold">,
  "reasoning": <string — one sentence written for a salesperson, naming the key signals>,
  "lead_completeness": <float — return unchanged from the value in LEAD DATA>,
  "sub_scores": {
    "fit":        <integer 0–25>,
    "intent":     <integer 0–25>,
    "engagement": <integer 0–20>,
    "behaviour":  <integer 0–20>,
    "context":    <integer 0–10>
  },
  "recommended_action": <string — one sentence, specific and immediately actionable>,
  "needs_review": <false>
}

Notes on specific fields:
- reasoning: Write for a salesperson, not an engineer. Example:
  "Strong ICP fit (CTO at funded SaaS co) and explicit high-intent signals
   (pricing + demo request + stated timeline) make this a high-priority lead."
- recommended_action: Be specific. Bad: "Follow up soon." Good: "Call today —
  confirm demo time and send the enterprise pricing deck."
- needs_review: Always return false. The system will set this to true if
  lead_completeness falls below the review threshold — you do not decide this.
- sub_scores: All five keys must always be present. A zero means no signal
  fired in that dimension, not that the field is optional.
```

### User Message

```
[TASK]
VARIANT: new

--- LEAD DATA ---
Name:           Rohan Mehta
Phone:          +91 98765 43210
Email:          rohan.mehta@techsolveindia.io
Company:        TechSolve India Pvt. Ltd.
Role:           CTO
Company size:   120 employees
Industry:       B2B SaaS / Cloud Software
Geography:      Mumbai, Maharashtra, India
City tier:      Tier 1
Source:         WhatsApp inbound
First contact:  2026-05-02
Channel:        WhatsApp (primary), Email (follow-up)

DATA COMPLETENESS: 0.87

--- SIGNAL VALUES ---

FIT SIGNALS:
  industry_match         : true
  role_relevance         : true
  company_size_fit       : true
  serviceability         : true

INTENT SIGNALS:
  pricing_request        : true
  demo_requested         : true
  urgency_language       : true
  timeline_stated        : true  (said "we want to make a decision this month")
  budget_mentioned       : false

ENGAGEMENT SIGNALS:
  response_speed         : fast  (replied within 2 hours to every message)
  revisit_count          : 3     (three separate conversation threads)
  channel_diversity      : multi  (WhatsApp + email)
  conversation_depth     : high  (7 message exchanges with substantive questions)
  follow_up_initiated    : true  (Rohan sent a follow-up on day 2 without prompting)

BEHAVIOUR SIGNALS:
  prior_customer         : false
  referral_source        : direct  (found Gamoft independently — no referral)
  content_engagement     : medium  (viewed pricing page twice, case study once)
  form_completion        : true

CONTEXT SIGNALS:
  geography_tier         : 1
  account_growth_signal  : true  (LinkedIn post from company page: "thrilled to
                                  announce our Series A funding round this week")
  seasonal_relevance     : neutral

Return JSON only.
```

### What a Correct Output Looks Like

```json
{
  "score": 86,
  "bucket": "hot",
  "reasoning": "Strong ICP fit (CTO at 120-person funded SaaS co, Tier 1 city) combined with four explicit high-intent signals (pricing, demo, urgency, stated timeline this month) and fast multi-channel engagement — this lead has all the hallmarks of a short-cycle, high-conversion opportunity.",
  "lead_completeness": 0.87,
  "sub_scores": {
    "fit": 23,
    "intent": 22,
    "engagement": 18,
    "behaviour": 14,
    "context": 9
  },
  "recommended_action": "Call today — confirm demo slot for this week and send the enterprise pricing deck before end of day.",
  "needs_review": false
}
```

### Annotations

| Element | Why it is written this way |
|---|---|
| `score: 86` | Sum of sub_scores: 23+22+18+14+9 = 86. Bucket HOT (≥80) is consistent. |
| `reasoning` | Mentions the tenant (Gamoft ICP match), the two strongest signals (fit + intent), and the engagement pattern. Written for a salesperson, not an engineer. |
| `sub_scores.fit: 23` | Near-maximum (max 25). All four Fit signals fired: industry, role, size, serviceability. Slight deduction because it is a first-time lead with no prior relationship. |
| `sub_scores.intent: 22` | Near-maximum (max 25). Four of five Intent signals fired. Only `budget_mentioned` is false — small deduction. |
| `sub_scores.behaviour: 14` | Moderate (max 20). No prior customer status and no referral weaken this dimension despite good content engagement and form completion. |
| `recommended_action` | Specific: confirms *what* (demo + pricing deck) and *when* (today / before end of day). Not generic. |
| `needs_review: false` | Completeness is 0.87 (≥ 0.80 threshold band). System confirms this after scoring. |

---

## 7. Sample Prompt 2 — SME Lead with Fragmented Context

### Setup

**Tenant:** Gamoft (same as Sample 1 — same system message, same ICP, same signal definitions).
**Lead type:** A small-to-medium business owner who sent a single WhatsApp message: "hi interested in your product". The Message Parser (Haiku) has already extracted what little structure exists from the message. The enrichment stage found no company registration, no public profile, and no prior contact history.
**Scenario:** This is a real-world case that will happen frequently — inbound contacts who express minimal intent, provide no company context, and cannot be fully enriched. The data completeness is 0.52 (52%).
**Variant:** `new`

**What makes this different from Sample 1:**
- Most signal values are `not_detected` or `false`
- Fit cannot be assessed because the company is unknown
- Intent is present but very weak (interested, but no specifics)
- Engagement is minimal (one message)
- Data completeness sits in the 50–79% WARNING band

**The system message is identical to Sample 1.** Only the user message (TASK section) changes. This is by design — the rules for handling missing signals are already in the system message ("If a signal value is `not_detected`, treat it as absent").

### System Message

*(Identical to Sample 1. Reprinted here for clarity.)*

```
[SYSTEM]
You are a lead scoring agent for a B2B SaaS company. Your job is to read the provided
lead data, evaluate the lead across five scoring dimensions, and return a structured
score as a JSON object.

[... same role, rules, rubric as Sample 1 ...]

RULES — THESE APPLY TO EVERY LEAD
1. Only use the signal values provided in the TASK section. ...
2. If a signal value is "not_detected", treat it as absent. Do not assume
   it is positive or negative. ...
3. Your reasoning must identify the two or three most important signals that
   drove the score — both signals that raised the score and any that lowered it.
   When data is sparse, your reasoning must explicitly name what is missing and
   why that limits the score.
4. Your recommended_action must be one sentence, specific to what a salesperson
   can do right now. For low-completeness leads, the recommended action should
   typically be a qualifying question.
5. Never collapse sub_scores. Always return all five dimensions.
6. Return the data completeness value exactly as provided. Do not change it.

[CONTEXT]
[... same business persona, ICP, signal weights as Sample 1 ...]

[OUTPUT FORMAT]
[... same JSON schema as Sample 1 ...]
```

### User Message

```
[TASK]
VARIANT: new

--- LEAD DATA ---
Name:           Unknown  (message sent from phone number; name not provided)
Phone:          +91 88001 12345
Email:          not_detected
Company:        not_detected  (no company name mentioned; no public profile found)
Role:           not_detected
Company size:   not_detected
Industry:       not_detected
Geography:      India  (confirmed by phone prefix +91; city unknown)
City tier:      not_detected
Source:         WhatsApp inbound
First contact:  2026-05-04
Channel:        WhatsApp only
Raw message:    "hi interested in your product"

DATA COMPLETENESS: 0.52

NOTE: Several signals could not be detected for this lead. Score using only
the signals that are present. Do not assume positive values for signals
marked not_detected. Your reasoning should note the most significant gaps.

--- SIGNAL VALUES ---

FIT SIGNALS:
  industry_match         : not_detected  (no company identified)
  role_relevance         : not_detected  (role unknown)
  company_size_fit       : not_detected  (company unknown)
  serviceability         : partial       (India confirmed; city and tier unknown)

INTENT SIGNALS:
  pricing_request        : false
  demo_requested         : false
  urgency_language       : false
  timeline_stated        : false
  budget_mentioned       : false

ENGAGEMENT SIGNALS:
  response_speed         : not_detected  (first contact; no reply from lead yet)
  revisit_count          : 1
  channel_diversity      : single        (WhatsApp only)
  conversation_depth     : low           (1 message, no substantive exchange)
  follow_up_initiated    : false

BEHAVIOUR SIGNALS:
  prior_customer         : false
  referral_source        : not_detected
  content_engagement     : not_detected
  form_completion        : false

CONTEXT SIGNALS:
  geography_tier         : not_detected
  account_growth_signal  : not_detected
  seasonal_relevance     : neutral

Return JSON only.
```

### What a Correct Output Looks Like

```json
{
  "score": 21,
  "bucket": "cold",
  "reasoning": "Almost no scoreable signals: Fit is unassessable (company unknown), Intent is minimal (a single 'interested' message with no pricing or demo request), and Engagement is at baseline (one message, no follow-up). The only positive signal is inbound interest on a valid India phone number — not enough to elevate the lead without qualifying information.",
  "lead_completeness": 0.52,
  "sub_scores": {
    "fit": 3,
    "intent": 4,
    "engagement": 5,
    "behaviour": 4,
    "context": 5
  },
  "recommended_action": "Send a short qualifying message asking for their company name and what specifically they are looking to solve — do not invest sales time until basic fit is confirmed.",
  "needs_review": false
}
```

**Note on needs_review:** The lead_completeness here is 0.52, which sits in the 50–79% WARNING band — not below the `needs_review` threshold. The system will add a WARNING flag to the score card when it processes this output, but will not route the lead to human review. If completeness had been below 0.50, the system would have set `needs_review: true` regardless of the LLM's returned value.

### Annotations

| Element | Why it is written this way |
|---|---|
| `score: 21` | Low but non-zero. The lead is real (inbound, valid phone), made contact (revisit_count: 1), and expressed some interest (one message). These prevent a zero score. Nothing else scored. |
| `reasoning` | Explicitly names what is missing (company, pricing request, follow-up). This is required by the framework's Rule 3 for low-completeness leads. Salesperson reads this and immediately understands why the score is low — not a system error. |
| `sub_scores.fit: 3` | Near-zero (max 25). Only `serviceability: partial` contributed. Three other Fit signals are `not_detected`. |
| `sub_scores.intent: 4` | Very low (max 25). The word "interested" in the message contributes a small amount, but no specific intent signals (pricing, demo, timeline) fired. |
| `sub_scores.context: 5` | Half of max (max 10). `seasonal_relevance: neutral` contributes nothing. `geography_tier` and `account_growth_signal` are both `not_detected`. The score receives a small baseline for being a confirmed India inbound. |
| `recommended_action` | Qualifies the lead rather than rushing to call. The salesperson's priority is to gather the missing information efficiently, not to invest call time on an unqualified lead. |
| Compare to Sample 1 | Sample 1 scored 86 (HOT, immediate call). Sample 2 scores 21 (COLD, qualifying message first). Same scoring framework, same tenant, same signal definitions — but the actual lead data tells a completely different story. |

---

## 8. What the Output Schema Layer Adds After the LLM Responds

The LLM returns the seven fields shown in the OUTPUT FORMAT section above. After the LLM responds, the **Output Schema Layer** (a deterministic system component, not an LLM) processes the output and adds three more fields before the final result is stored:

| Field added by Output Schema Layer | Where it comes from |
|---|---|
| `schema_version` | The current version of the ScoringOutput schema (e.g., `"v1.0"`) — set by the system |
| `prompt_version` | The active prompt version for this tenant (e.g., `"v1.3.0"`) — loaded from `prompt_registry` |
| `model` | Which AI model served this specific call (e.g., `"claude-sonnet-4-6"`) — taken from the API response |

The Output Schema Layer also performs three checks before storing:

1. **Banding enforcement:** If the LLM's `bucket` does not match what the `score` + tenant thresholds would produce, the threshold-derived bucket wins. The discrepancy is logged. This ensures mathematical consistency between the score and the bucket regardless of what the LLM said.

2. **needs_review gate:** If `lead_completeness` is below the configured threshold (currently 0.60 or 0.75 — team decision pending), the system overrides the LLM's `needs_review: false` with `true`. The lead is routed to the human review queue. It is still scored and still delivered — just flagged.

3. **Schema validation:** All fields are type-checked and coerced (e.g., bucket string is lowercased, score is rounded to integer). If validation fails, the system retries once before returning a ScoringFailure.

The complete stored record (after Output Schema Layer processing) is:

```json
{
  "score": 86,
  "bucket": "hot",
  "reasoning": "...",
  "lead_completeness": 0.87,
  "sub_scores": { "fit": 23, "intent": 22, "engagement": 18, "behaviour": 14, "context": 9 },
  "recommended_action": "...",
  "needs_review": false,
  "schema_version": "v1.0",
  "prompt_version": "v1.3.0",
  "model": "claude-sonnet-4-6"
}
```

---

## 9. Open Decisions

These decisions affect how prompts are stored and managed but do not change the framework structure itself.

| Decision | Current status | Impact on prompts |
|---|---|---|
| **Prompt storage location:** in code (git-versioned) vs in the database (editable without deployment) | `[TBD — team decision]` | Git storage means a deployment is required every time a prompt is updated. DB storage allows hot changes but adds a management interface. Framework is the same either way. |
| **Model config scope:** single global model vs per-tenant model override | `[TBD — team decision]` | If per-tenant overrides are supported, the CONTEXT section would include a model preference field that the system reads before making the API call. |
| **needs_review threshold:** 0.60 (lenient) vs 0.75 (conservative) | `[TBD — team decision after Month 1 data]` | Affects how often low-completeness leads are routed to human review. Does not change the prompt template itself. |
| **Per-tenant signal count:** number of signals per dimension | Intent ≥5, Engagement ≥6 confirmed; others TBD per tenant | More signals = longer CONTEXT section = higher token count per system message. Caching partially offsets this, but very large signal sets may push the system message toward context window limits. |

---

## Evidence

- Prompt Prompt Layer mechanics (static system message, per-lead user message, caching behaviour): [[analyses/rating-agent-spec]] Component 2 — Prompt Layer
- Fill-in-the-blanks template structure and signal slot design: [[analyses/orchestration-layer-spec]] Section 4.3 Stage 4
- Scoring dimensions, default weights, and sub_scores schema: [[concepts/signal-types]]
- PersonaObject and ICP structures injected into CONTEXT section: [[analyses/persona-agent-spec]] Steps 1 and 2
- Intelligence Layer four-component pipeline (Persona Engine → Prompt Layer → Rating Agent → Output Schema Layer): [[concepts/intelligence-layer]]
- lead_completeness field naming correction (not LLM confidence): [[concepts/confidence-first-class]]
- Output Schema Layer banding enforcement and needs_review gate: [[analyses/rating-agent-spec]] Component 4 — Output Schema Layer
- Three prompt variants (new / returning / rescore): [[analyses/rating-agent-spec]] The Three Prompt Variants section
- Message Parser (Haiku) as second LLM call on DM path: [[analyses/global-data-collection-architecture]] Revised LLM Call Principle

---

## Caveats & Gaps

- **Samples cover Rating Agent only.** The Message Parser and Persona Agent prompt structures follow the same four-section framework but are not shown here. Writing those samples is a separate task.
- **Samples use `new` variant only.** The `returning` and `rescore` variant structures (prior score and touchpoint history injection) are described in Section 4 but not demonstrated with full examples.
- **Signal weights in samples are illustrative.** The actual signal weights for the Gamoft tenant are set by the Persona Agent during onboarding. The weights shown in Sample 1 are representative starting points.
- **needs_review threshold is not yet confirmed.** The framework describes what happens at both 0.60 and 0.75 thresholds; the actual value is a team decision pending Month 1 data. See [[analyses/rating-agent-spec]] Open Decisions.
- **Prompt storage format is not yet decided.** The framework describes what the prompts contain, not where they are stored (code vs database). See Open Decisions above.

---

## Follow-up Questions

- Should the `returning` variant sample be documented as a separate analysis or added to this document?
- Should Persona Agent prompt templates (Steps 1, 2, 3) be written and filed here, or as a separate analysis linked from [[analyses/persona-agent-spec]]?
- Once the needs_review threshold is confirmed (Month 1 decision), this document should be updated to reflect the live value.
- Are there any non-scoring LLM interactions planned beyond the five call types listed in Section 5? If so, they should be added to the framework coverage table.
