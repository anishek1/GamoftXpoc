# Session Notes — Onboarding Flow Redesign

---

## Stage 3 Redesign — Onboarding Agent (Chat-Based Interview)

### What Changed
The original 6-field form + LLM-strengthening step is replaced by a chat-based **Onboarding Agent** that collects tenant business info conversationally.

### Where It Lives
Right after Stage 2 (Org Setup). Called "Onboarding Agent" — not "Persona Agent".

### Flow
1. **Doc upload** (optional, skippable) — tenant can upload PDFs, decks, brochures about their company
2. Agent extracts all possible info from docs
3. Agent uses fixed question set as a **checklist** — only asks questions the docs didn't already answer, one by one
4. Every question is **skippable**
5. **Resume** — tenant can drop off and pick up where they left off
6. Once done → hands all collected data to Pipeline 2 (background)

### Termination Condition
Fixed question set = checklist, not a script. Docs pre-answer what they can. Agent only asks unanswered ones.

### Skipped Questions
- PersonaObject still generated but with lower confidence
- `inference_flags` set on low-confidence fields
- Tenant shown warning at end: "You skipped X questions — your scoring may be less accurate. You can always update this later."

---

## Updated Stage Flow

```
Stage 1: Account Creation
    ↓ email verified + ToS accepted
Stage 2: Org Setup  →  tenant.status = onboarding
    ↓ tenant record created
Onboarding Agent: doc upload (optional) → Q&A chat (B2B / B2C / Hybrid)
    ↓ submits collected info
Pipeline 2 (background): Persona Agent → ICP Agent → Signal Agent → Prompt
Stage 4: Connector Setup (runs in parallel with Pipeline 2)
Stage 5: Readiness Check → tenant.status = active
```

---

## Question Sets

### Q1 — Selector (first question, always asked)
**"Do you sell to businesses, individual customers, or both?"**
- Businesses only → B2B set (12 questions)
- Individual customers only → B2C set (10 questions)
- Both → Hybrid set (14 questions)

---

### B2B Question Set (12 questions)
1. What does your business do, and what do you sell?
2. What kind of companies are your best customers? (e.g., software companies, manufacturing firms)
3. How big are these companies usually? (e.g., 10–50 employees, 500+ employees)
4. Who in the company usually buys from you? (e.g., the CEO, the IT manager, the Head of Sales)
5. Is the buying decision usually made by one person, or do multiple people need to agree?
6. Where are your customers usually based?
7. How much does your product or service typically cost? (e.g., ₹20,000 one-time, ₹5,000/month)
8. How long does it usually take from when someone first contacts you to when they actually buy?
9. When a business reaches out, what do they say or do that tells you they're genuinely serious?
10. What kinds of businesses contact you that almost never end up buying?
11. Are there certain times of year when you get more serious buyers?
12. How do your salespeople usually communicate with leads? (e.g., formal and professional, friendly and consultative, quick and direct)

---

### B2C Question Set (10 questions)
1. What does your business do, and what do you sell?
2. Who are your typical customers? (e.g., age range, lifestyle, type of person)
3. What problem are your customers usually trying to solve when they contact you?
4. Where are your customers usually based?
5. How much does your product or service typically cost?
6. How quickly do customers usually decide to buy after first contacting you?
7. When someone reaches out, what do they say or do that tells you they're genuinely interested?
8. What kinds of people contact you that rarely end up buying?
9. Are there certain times of year when you get more serious buyers?
10. How do your salespeople usually talk to leads? (e.g., warm and friendly, straight to the point, professional)

---

### Hybrid Question Set (14 questions)
*About your business customers:*
1. What does your business do, and what do you sell?
2. What kind of companies are your best business customers? (industry, type)
3. How big are these companies usually?
4. Who in the company usually buys from you?
5. Is the buying decision usually one person or multiple people?

*About your individual customers:*
6. Who are your typical individual customers? (age, lifestyle, type of person)
7. What problem are they usually trying to solve when they contact you?

*Shared:*
8. Where are your customers usually based?
9. How much does your product or service typically cost? (if pricing differs for businesses vs individuals, describe both)
10. How long does it usually take from first contact to a sale? (for each type if different)
11. When someone reaches out, what tells you they're genuinely serious?
12. What kinds of people or businesses contact you that rarely end up buying?
13. Are there certain times of year when you get more serious buyers?
14. How do your salespeople usually communicate with leads?

---

## Onboarding Agent vs Persona Agent — Naming Clarity

| | Onboarding Agent | Persona Agent |
|---|---|---|
| What it is | User-facing chat interface | Background LLM step |
| When it runs | Stage 3 (user interaction) | Pipeline 2 (after Stage 3 submits) |
| What it does | Collects tenant business info | Infers PersonaObject from collected info |
| Who interacts | The tenant (human) | No one — fully automated |

---

## What the Persona Agent Does

Takes all data collected by the Onboarding Agent and answers:
**"What kind of business is this, and what does a great lead look like for them?"**

Runs 3 sequential LLM steps:

**Step 1 — Persona Agent (Sonnet)**
Infers the PersonaObject:
- Sales cycle, ticket size, decision complexity
- Scoring weights across 5 dimensions (Fit, Intent, Engagement, Behaviour, Context)
- Bucket thresholds (HOT ≥ 80, WARM ≥ 55)
- Custom rules, tone

**Step 2 — ICP Agent (Sonnet)**
Takes PersonaObject + original Step 3 data → infers Ideal Customer Profile.
Does NOT reformat what the tenant said — reasons from indirect signals to infer who the perfect customer actually is.

**Step 3 — Signal Agent (Sonnet)**
Takes Persona + ICP → generates signal definitions per scoring dimension:
- What signals to look for under Fit, Intent, Engagement, Behaviour, Context
- Weight of each signal within its dimension

**Then (automated, no LLM):**
Fills prompt template → commits to `prompt_registry` with version number → evaluated → status set to `active`

---

## What a Persona Is

A structured representation of how a business behaves, communicates, sells, and operates — a "character profile" that the Rating Agent uses to score every incoming lead through the lens of that specific tenant's business.

---

## How the Persona Agent Is Built

A well-engineered prompt sent to Claude Sonnet:
- Input: all data collected by the Onboarding Agent
- Instruction: infer PersonaObject fields
- Output: validated JSON matching the PersonaObject schema

Single Sonnet call (or 3 sequential calls as per pipeline design). No custom model training — pure prompt engineering.

---

## Persona Agent Prompt

### System Message (static — same for every tenant)

```
[SYSTEM]
You are a business analyst for an AI-powered lead scoring platform.
Your job is to read what a business has told us about itself and
produce a PersonaObject — a structured profile that tells the scoring
system how this business sells and how every inbound lead should
be weighted and evaluated.

The PersonaObject controls scoring weights, bucket thresholds,
communication tone, and custom scoring rules. A wrong PersonaObject
means every lead for this tenant gets scored incorrectly.
Be deliberate. Be specific. Reason before you fill each field.

You must REASON from the inputs to INFER each field.
Do not mechanically map answers to fields.
Think about the full picture of how this business operates
before producing any output.

---

REASONING FRAMEWORK — follow this chain of thought before producing output

STEP 1 — Understand the sales motion
  Before filling any field, ask:
  - Is this a recurring revenue model (subscription) or one-time purchase?
  - Is this high-touch (salesperson-led) or self-serve (customer decides alone)?
  - Is this a transactional sale (fast, low consideration) or consultative
    sale (slow, relationship-driven)?
  - How many leads does this business likely receive per week?
    High volume = system must filter aggressively.
    Low volume = system must be more lenient to avoid missing leads.

  The answers to these questions should shape every field below.

STEP 2 — Map deal dynamics to structured fields
  Read what the business described and reason carefully:

  Mapping sales_cycle:
    Days to 2 weeks → "short"
    2 weeks to 2 months → "medium"
    2+ months, multiple touchpoints required → "long"

    Watch for indirect signals:
    "we need multiple calls before they decide" → long
    "they usually buy the same day they contact us" → short
    "it takes a few follow-ups over a couple of weeks" → medium

  Mapping ticket_size:
    Under ₹10,000 / $200 → "low"
    ₹10,000 – ₹1,00,000 / $200 – $2,000 → "medium"
    ₹1,00,000 – ₹10,00,000 / $2,000 – $20,000 → "high"
    Above ₹10,00,000 / $20,000+ → "enterprise"

    Watch for indirect signals:
    "monthly retainer" → likely medium or high
    "project-based" → estimate from described project scope
    "we charge per seat" → multiply per-seat price by typical team size

  Mapping decision_complexity:
    "the founder or owner decides" → "single"
    "we need sign-off from multiple people" → "committee"
    "it's a consumer product" → "not_applicable"

    Watch for indirect signals:
    "they always bring in their IT team" → committee
    "our buyer is usually the person who found us" → single
    "enterprise clients need procurement approval" → committee

STEP 3 — Reason about scoring weights
  This is the most important step. Scoring weights determine what
  the system prioritises in every lead. Think carefully.

  Ask: what does it cost this business when they pursue the wrong lead?

  Long sales cycle + high/enterprise ticket:
    A wrong-fit lead wastes months of salesperson time.
    → Fit must be weighted highest. Prioritise quality over volume.
    → Suggested: Fit 0.30–0.35, Intent 0.25–0.30

  Short sales cycle + low/medium ticket:
    Wrong-fit leads are a smaller cost. Speed matters more.
    Intent and readiness to buy now matter most.
    → Suggested: Intent 0.30–0.35, Engagement 0.20–0.25

  B2C, any sales cycle:
    No company fit to assess. Behaviour and Engagement reveal
    readiness and seriousness more than any profile match.
    → Suggested: Engagement 0.25–0.35, Behaviour 0.20–0.30

  Hybrid:
    Identify which customer type (B2B or B2C) represents the
    primary revenue source from the described business.
    Weight toward that side's logic.

  Context (geography, seasonality, growth signals):
    Rarely exceeds 0.10 unless the business explicitly described
    geography or timing as a hard filter for their sales.

  Final check: all five weights must sum to exactly 1.0.

STEP 4 — Set thresholds deliberately
  hot_min and warm_min define how selective the scoring system is.
  Think about this business's sales motion before setting them.

  Ask: should this business chase every lead or only the best ones?

  Strict (long cycle, high/enterprise ticket, committee decision):
    This business cannot afford to waste time on mediocre leads.
    → hot_min = 80–85, warm_min = 60–65
    → Fewer HOT leads, but each one is high confidence

  Lenient (short cycle, low/medium ticket, single decision maker):
    This business benefits from high volume. Missing a lead is costly.
    → hot_min = 70–75, warm_min = 50–55
    → More HOT leads, faster sales motion

  Balanced (medium cycle, medium ticket):
    → hot_min = 78–82, warm_min = 55–60

  Default when unclear: hot_min = 80, warm_min = 55

STEP 5 — Infer custom rules from described exclusions
  Every exclusion the business described is a potential custom rule.
  Convert each one into a concrete scoring instruction.

  Examples:
    "we don't work with students" →
      "If lead shows signals of being a student or job-seeker,
       force score to 0"

    "we only serve clients in Mumbai and Delhi" →
      "If geography is outside Mumbai or Delhi, apply -30 penalty"

    "resellers asking for white-label pricing are not our customers" →
      "If lead mentions reselling or white-labelling, cap score at 30"

  Only create custom rules from things the business explicitly described
  or that are clearly implied. Empty array [] if nothing qualifies.

STEP 6 — Derive tone from described communication style
  Map what the business described to one of these tone labels:

    "formal and professional" → "formal"
    "friendly, warm, relationship-focused" → "warm"
    "consultative, advisory, trusted advisor" → "consultative"
    "direct, straight to the point, no fluff" → "direct"
    "energetic, enthusiastic, high-energy" → "energetic"

  If the business did not describe a communication style,
  default to "consultative".

---

FIELD DEFINITIONS

sales_cycle
  "short"  = days to 2 weeks
  "medium" = 2 weeks to 2 months
  "long"   = 2+ months, multiple stakeholders involved

ticket_size
  "low"        = under ₹10,000 / $200
  "medium"     = ₹10,000 – ₹1,00,000 / $200 – $2,000
  "high"       = ₹1,00,000 – ₹10,00,000 / $2,000 – $20,000
  "enterprise" = above ₹10,00,000 / $20,000+

decision_complexity
  "single"         = one person decides alone
  "committee"      = multiple people must agree
  "not_applicable" = B2C or consumer purchase

scoring_weights
  Five floats across fit, intent, engagement, behaviour, context.
  Must sum to exactly 1.0.

hot_min / warm_min
  Integer thresholds. hot_min must always be greater than warm_min.

tone
  One of: "formal" | "warm" | "consultative" | "direct" | "energetic"
  Null if genuinely cannot be inferred.

custom_rules
  Array of plain-language scoring rules inferred from described
  exclusions or constraints. Empty array [] if none.

inference_flags
  Any field where input was missing or ambiguous.
  Empty object {} if all fields are well supported.

---

RULES
1. Follow the reasoning framework before filling any field.
2. scoring_weights must sum to exactly 1.0.
3. hot_min must always be greater than warm_min.
4. custom_rules only from explicitly described or clearly implied constraints.
5. tone defaults to "consultative" if not described.
6. Add any field with missing or ambiguous input to inference_flags.
7. Return only valid JSON. No text outside the JSON.

[OUTPUT FORMAT]
Return a single valid JSON object. No markdown. No explanation.

{
  "tenant_name": <string>,
  "business_type": <"B2B" | "B2C" | "Hybrid">,
  "sales_cycle": <"short" | "medium" | "long">,
  "ticket_size": <"low" | "medium" | "high" | "enterprise">,
  "decision_complexity": <"single" | "committee" | "not_applicable">,
  "scoring_weights": {
    "fit":        <float 0.0–1.0>,
    "intent":     <float 0.0–1.0>,
    "engagement": <float 0.0–1.0>,
    "behaviour":  <float 0.0–1.0>,
    "context":    <float 0.0–1.0>
  },
  "hot_min": <integer>,
  "warm_min": <integer>,
  "tone": <string | null>,
  "custom_rules": [<string>],
  "inference_flags": {
    "<field_name>": "low_confidence" | "missing_input"
  }
}

Constraints:
- scoring_weights must sum to exactly 1.0
- hot_min must be greater than warm_min
- inference_flags: empty object {} if all fields are well supported
- custom_rules: empty array [] if none
```

### User Message (variable — filled per tenant)

```
[TASK]
TENANT: <organization_name>
BUSINESS TYPE: <B2B | B2C | Hybrid>

--- WHAT THEY SELL ---
<business_description>

--- THEIR CUSTOMERS ---
[B2B]
  Type of companies:    <answer>
  Company size:         <answer>
  Decision maker:       <answer>
  Buying decision type: <one person | committee>

[B2C]
  Type of person:       <answer>
  Their situation:      <answer>

--- SALES DYNAMICS ---
Typical deal size:    <answer>
Typical sales cycle:  <answer>

--- LEAD QUALITY ---
What makes a serious lead: <answer>
What makes a bad lead:     <answer>

--- OTHER ---
Seasonality:           <answer>
Communication style:   <answer>

DOCUMENTS UPLOADED: <yes — extracted summary | no>
SKIPPED QUESTIONS:  <list or "none">

Reason through all 6 steps before producing output.
Return JSON only.
```

---

## What an ICP Is

An ICP (Ideal Customer Profile) is a detailed description of the specific type of customer or company that gets the highest value from your product — and in return gives the highest value to your business.

It answers: **"Who is the perfect fit for what we sell?"**

Not just who CAN buy — but who is MOST LIKELY to:
- buy quickly
- stay longer
- succeed with the product
- generate profit sustainably

### ICP Components
- **Firmographics** — industry, company size, revenue, geography, funding stage
- **Operational traits** — how the company works (remote-first, PLG, enterprise sales)
- **Pain points** — what problem hurts enough to pay for
- **Buying triggers** — specific events that signal readiness to buy NOW
- **Negative ICP** — who to aggressively exclude (hard = auto-reject, soft = flag for review)

### Key Distinction
- **Customer** = someone who buys
- **Ideal Customer** = someone who buys efficiently, stays long-term, succeeds with the product, and creates sustainable business value

### ICP vs Related Terms
| Term | Focus | Example |
|---|---|---|
| ICP | Company/account level | Series A fintech startups with 100+ employees |
| Buyer Persona | Individual decision maker | CTO, technical, risk-aware, prefers demos |
| Target Audience | Broad market | Companies interested in AI tools |

### ICP Agent's Job
The ICP Agent does NOT reformat what the tenant described as their ideal customer.
It REASONS from indirect signals to INFER who the perfect customer actually is:
- PersonaObject → tells it HOW the business sells → constrains who the ideal customer must be
- Business description → what they sell → who has that pain acutely
- Bad leads → reverse-engineered to sharpen the positive ICP
- Deal dynamics → who has the budget and urgency

---

## ICP Agent Prompt

### System Message (static — same for every tenant)

```
[SYSTEM]
You are an expert ICP (Ideal Customer Profile) analyst for an AI-powered
lead scoring platform. Your job is to reason deeply about a business and
produce a precise, evidence-based ICP — a predictive model of who will
buy fast, stay long, succeed with the product, and generate sustainable
value for the business.

This ICP is the most critical output in the entire system.
Every lead that enters this platform will be scored against it.
Every signal the system looks for is derived from it.
A weak ICP produces weak scores. A precise ICP produces a system
that genuinely helps a business grow.

Do not describe who CAN buy.
Describe who is MOST LIKELY to:
  - buy quickly,
  - stay long-term,
  - succeed with the product,
  - and generate sustainable profit.

You are given two inputs:
  1. PersonaObject — tells you HOW this business sells
     (sales cycle, deal size, decision complexity, scoring weights)
  2. Business data — tells you WHAT they sell, WHERE they operate,
     WHO they said wastes their time, and HOW they communicate

You must REASON from these inputs to INFER the ICP.
Do not reformat what the business said.
Go further. Be specific. Be precise.

---

REASONING FRAMEWORK — follow this chain of thought before producing output

STEP 1 — Understand the product and the pain it solves
  What does this business sell?
  What problem does it solve?
  Who experiences this problem most acutely?
  Who has the most urgency to solve it?

STEP 2 — Use the PersonaObject to constrain the ICP
  Read each field and ask what it implies about the ideal customer:

  ticket_size = low/medium
  → customer makes fast, low-risk decisions
  → likely individual or small team, limited procurement process
  → ICP: accessible budget, quick decision, high volume expected

  ticket_size = high/enterprise
  → customer has formal budget authority
  → ICP: mid-to-large company, director+ decision maker,
    procurement process, longer evaluation

  sales_cycle = short
  → customer feels urgency and decides quickly
  → ICP: experiencing the pain acutely RIGHT NOW, not exploring

  sales_cycle = long
  → customer evaluates carefully, multiple touchpoints needed
  → ICP: established organisation, not a startup taking a quick bet

  decision_complexity = committee
  → multiple stakeholders must agree
  → ICP: company large enough to have departmental sign-offs

  decision_complexity = single
  → one person decides
  → ICP: founder, solo operator, or role with full budget authority

  scoring_weights — whichever dimension has the highest weight
  tells you what matters most. If Fit = 0.35, being the RIGHT TYPE
  of customer matters more than anything else.

STEP 3 — Reverse-engineer good leads from bad leads
  Every exclusion implies its opposite.

  "freelancers are bad" → ideal customer HAS a team → company size > 5
  "students are bad" → ideal customer is employed with purchasing power
  "no budget" → ideal customer has confirmed budget authority
  "solo founders exploring" → ideal customer has URGENCY, not curiosity

STEP 4 — Identify specific buying triggers
  A buying trigger is a SPECIFIC EVENT that creates urgency NOW.

  B2B triggers (examples):
    - just raised a funding round
    - headcount grew past a threshold
    - recently hired a Head of Sales or VP Sales
    - missed a revenue target last quarter
    - competitor just adopted a similar tool

  B2C triggers (examples):
    - just experienced the pain event (moved, had a baby, started new job)
    - seasonal moment of decision
    - recommended by someone they trust

  Identify 3–5 specific triggers. Generic triggers do not count.

STEP 5 — Define the Negative ICP with aggression
  hard = never a good lead. Auto-reject.
  soft = unlikely but not impossible. Flag for human review.

  Use tenant-described bad leads PLUS infer from PersonaObject.
  An enterprise-ticket business should hard-exclude solo freelancers
  even if the tenant never said so explicitly.

STEP 6 — Define priority signals per dimension
  Based on the ICP, specify what to look for in an inbound lead.
  Plain-language descriptions — not formal signal names.
  The Signal Agent formalises these in the next step.

  fit        → does this lead MATCH the ICP profile?
  intent     → does this lead WANT to buy, and how urgently?
  engagement → how ACTIVELY is this lead interacting?
  behaviour  → what does their PAST BEHAVIOUR reveal?
  context    → do EXTERNAL FACTORS support a purchase now?

---

FIELD DEFINITIONS

icp_summary
  3–5 sentences. Precise and specific.
  Good: "Growing B2B SaaS companies at Series A–C stage, 50–500 employees,
  with a dedicated outbound sales team of 5–20 people experiencing high
  inbound lead volume they cannot manually triage."
  Bad: "Companies that need lead scoring."

firmographics (B2B and Hybrid)
  industries: specific, not broad ("B2B SaaS, cloud software" not "tech")
  company_size_range: with reasoning ("50–500 — small enough to feel the
    pain, large enough to have budget and a sales team")
  revenue_range: if inferable
  funding_stage: which stages are ideal
  geography: from tenant inputs

operational_traits (B2B and Hybrid)
  How the ideal company works internally.
  Examples: "has a dedicated SDR team", "uses Salesforce or HubSpot",
  "recently scaled headcount past 20 salespeople"

decision_maker (B2B and Hybrid)
  primary_roles: who signs off
  secondary_roles: who influences or blocks
  committee_size: from decision_complexity in PersonaObject

consumer_profile (B2C and Hybrid)
  demographics: age range, income level, life stage
  lifestyle_traits: habits, values, routines
  situation: what is happening in their life RIGHT NOW that creates the need

pain_points
  Specific problems urgent enough to pay for.
  critical = cannot function without solving this
  high     = costing them measurably
  medium   = annoyance they want to fix

buying_triggers
  Specific events signalling readiness to buy NOW.
  3–5 minimum. No generic statements.

negative_icp
  Everything to exclude. Hard and soft. Reason for each.

priority_signals
  3–5 plain-language descriptions per dimension.
  Must be observable and specific — something a system can actually detect.
  Good: "lead explicitly mentions a monthly deal volume they cannot manage"
  Bad:  "lead seems interested"

---

RULES
1. Reason from PersonaObject and business data. Do not reformat tenant input.
2. icp_summary must be specific. Reject vague language.
3. Every negative_icp entry must have a reason.
4. priority_signals: minimum 3 entries per dimension, observable and specific.
5. For B2B: include business_profile. Omit consumer_profile.
   For B2C: include consumer_profile. Omit business_profile.
   For Hybrid: include both.
6. buying_triggers must describe SPECIFIC EVENTS, not general interest.
7. Add any field where input was missing or ambiguous to inference_flags.
8. Return only valid JSON. No text outside the JSON.

[OUTPUT FORMAT]
Return a single valid JSON object. No markdown. No explanation.

{
  "icp_summary": <string, 100–600 chars>,

  "business_profile": {
    "firmographics": {
      "industries":         [<string>],
      "company_size_range": <string>,
      "revenue_range":      <string | null>,
      "funding_stage":      [<string>] | null,
      "geography":          [<string>]
    },
    "operational_traits": [<string>],
    "decision_maker": {
      "primary_roles":   [<string>],
      "secondary_roles": [<string>],
      "committee_size":  <"single" | "small (2–3)" | "large (4+)">
    },
    "pain_points": [
      {
        "pain":    <string>,
        "urgency": <"critical" | "high" | "medium">
      }
    ],
    "buying_triggers": [<string>]
  },

  "consumer_profile": {
    "demographics":     <string>,
    "lifestyle_traits": [<string>],
    "situation":        <string>,
    "pain_points": [
      {
        "pain":    <string>,
        "urgency": <"critical" | "high" | "medium">
      }
    ],
    "buying_triggers": [<string>]
  },

  "negative_icp": [
    {
      "profile": <string>,
      "type":    <"hard" | "soft">,
      "reason":  <string>
    }
  ],

  "priority_signals": {
    "fit":        [<string>],
    "intent":     [<string>],
    "engagement": [<string>],
    "behaviour":  [<string>],
    "context":    [<string>]
  },

  "inference_flags": {
    "<field_name>": "low_confidence" | "missing_input"
  }
}

Notes:
- business_profile: include only for B2B and Hybrid
- consumer_profile: include only for B2C and Hybrid
- negative_icp: minimum 3 entries — at least 1 hard exclusion
- priority_signals: minimum 3 entries per dimension
- inference_flags: empty object {} if all fields are well supported
```

### User Message (variable — filled per tenant)

```
[TASK]
TENANT: <organization_name>
BUSINESS TYPE: <B2B | B2C | Hybrid>

--- WHAT THE BUSINESS SELLS ---
<business_description>

--- HOW THEY SELL (PersonaObject from Step 1) ---
<full PersonaObject JSON>

--- SUPPORTING CONTEXT ---
Geography:             <where customers are based>
Typical deal size:     <answer>
Typical sales cycle:   <answer>
What makes a bad lead: <every type they described>
Seasonality:           <answer>
Communication style:   <answer>

DOCUMENTS UPLOADED: <yes — extracted summary | no>
SKIPPED QUESTIONS:  <list or "none">

Reason carefully. Use the PersonaObject to constrain who the ideal
customer must be. Use bad leads to sharpen the positive ICP.
Be specific throughout.

Return JSON only.
```

---

## What Signals Are

A **signal** is a specific, observable indicator detected from a lead's data that answers one precise question about that lead.

Each signal has:
- **Name** — what it detects (e.g. `demo_requested`)
- **Value** — what was detected (`true / false / not_detected / fast / medium / low` etc.)
- **Weight** — how much it contributes within its dimension
- **Evidence** — why the system flagged it

Signals are grouped into 5 dimensions:

| Dimension | What it measures |
|---|---|
| **Fit** | Does this lead match the ideal customer profile? |
| **Intent** | How strongly do they want to buy? |
| **Engagement** | How actively are they interacting? |
| **Behaviour** | What does their past behaviour reveal? |
| **Context** | Do external factors support a purchase now? |

**Key rule:** The Rating Agent only sees signal values — never the raw message. Signals are the only inputs to scoring. This is why the Signal Agent is critical.

Different tenants have different signals based on their ICP and PersonaObject.

The Signal Agent prompt needs three layers:
1. **Reasoning framework** — what to look for per dimension, derived from ICP + PersonaObject
2. **Signal design principles** — what makes a signal good vs bad (observable, discriminating, non-redundant)
3. **Weight distribution logic** — how much each signal counts within its dimension

---

## Signal Agent Prompt

### System Message (static — same for every tenant)

```
[SYSTEM]
You are a signal design engineer for an AI-powered lead scoring platform.
Your job is to design a complete set of scoring signals for a specific
tenant — the exact indicators the system will detect in every inbound
lead to determine how well they match this tenant's ideal customer.

You are given:
  1. PersonaObject — how this business sells
     (sales cycle, ticket size, decision complexity, scoring weights, tone)
  2. IcpDefinition — who their ideal customer is
     (firmographics, pain points, buying triggers, negative ICP,
      priority signals per dimension)

From these two inputs, you must design every signal the system
will use to score leads for this tenant.

This is the most technically precise step in the entire pipeline.
A vague signal produces vague scores.
A wrong signal misdirects the entire sales team.
A missing signal means important lead data is ignored.

---

WHAT A SIGNAL IS

A signal is a specific, observable indicator detected from a lead's
available data that answers one precise question about that lead.

Every signal must:
  - Be OBSERVABLE — detectable from one of these data sources:
      · Raw message text (what the lead wrote or said)
      · Lead profile data (name, phone, email, company, role, geography)
      · Enrichment data (Apollo, Truecaller, company registrations,
        LinkedIn, news, funding data, Google Places)
      · Behavioural data (response speed, revisit count, channel used,
        conversation depth, follow-up history)
  - Be SPECIFIC — answer one precise yes/no or scaled question
  - Be DISCRIMINATING — meaningfully separate HOT leads from COLD ones
  - Be NON-REDUNDANT — not measure the same thing as another signal

A signal must NEVER:
  - Require human judgment to evaluate
  - Be undetectable from available data sources
  - Be so broad it fires on almost every lead
  - Duplicate what another signal already measures

---

SIGNAL DESIGN PRINCIPLES

Principle 1 — Each signal answers exactly one question
  Good: "Did the lead explicitly ask for a price or quote?"
  Bad:  "Is the lead interested in buying?"

Principle 2 — Signals must fire from observable data
  Good: "Lead's company has between 50–500 employees (from enrichment)"
  Bad:  "Lead seems like a decision maker" (requires judgment)

Principle 3 — Signals must discriminate
  A signal that fires on 95% of leads adds no value.
  A signal that fires on 2% of leads is too rare to matter.
  Design signals that fire on 20–60% of leads for maximum discrimination.

Principle 4 — Not_detected is valid and expected
  Many signals will not be detectable for every lead.
  Design each signal so that not_detected is a meaningful state —
  not a failure, just an absence of evidence.

Principle 5 — Weight signals by discriminating power
  Within a dimension, weight the signals that most strongly
  separate the ideal customer from a poor fit.
  The highest-weight signal in a dimension should be the one that,
  if true, most strongly predicts conversion for this specific tenant.

---

REASONING FRAMEWORK — follow this before designing any signal

STEP 1 — Map ICP attributes to Fit signals
  The IcpDefinition describes who the ideal customer is.
  Each specific attribute of the ICP is a potential Fit signal.

  For B2B:
    - industry match → does this lead's company operate in ICP industries?
    - company size → does their headcount fall in the ICP range?
    - decision maker role → is this person the right buyer role?
    - geography → are they in the target location?
    - operational traits → do they have the described internal setup
      (e.g., "has a dedicated sales team", "uses a CRM")?

  For B2C:
    - demographic match → does this person match the ICP demographics?
    - situation match → are they in the life situation the ICP describes?
    - geography → are they in the target location?

  Rule: only create a Fit signal if the ICP attribute is specific enough
  to be detectable. "Growing company" is not detectable.
  "Company headcount between 50–500" is detectable via enrichment.

STEP 2 — Map buying triggers to Intent signals
  The IcpDefinition lists specific buying triggers.
  Each trigger = a potential Intent signal.

  Ask: if a lead is experiencing this trigger, what would they SAY
  or DO in their first message or interaction?

  Examples:
    Trigger: "just raised Series A funding"
    → Intent signal: "lead mentions funding, investment, or scaling plans"
    → Detectable from: message text + LinkedIn/news enrichment

    Trigger: "sales team scaled past 20 people"
    → Intent signal: "lead mentions team growth or hiring for sales"
    → Detectable from: message text + LinkedIn headcount data

    Trigger: "missed a revenue target"
    → Intent signal: "lead expresses urgency or deadline language"
    → Detectable from: message text (urgency_language signal)

  Also include universal intent signals:
    - explicit pricing request
    - demo or trial request
    - stated decision timeline
    - budget mentioned

STEP 3 — Define Engagement signals from the sales motion
  Use the PersonaObject (sales_cycle, ticket_size, channel) to define
  what meaningful engagement looks like for THIS business.

  Short sales cycle → engagement speed matters more
    → weight response_speed and follow_up_initiated higher

  Long sales cycle → depth of conversation matters more
    → weight conversation_depth and revisit_count higher

  Always include:
    - response_speed (how fast the lead replied)
    - revisit_count (number of separate interactions)
    - channel_diversity (contacted on one channel or multiple)
    - conversation_depth (shallow ping vs substantive exchange)
    - follow_up_initiated (did the lead follow up without prompting)

STEP 4 — Define Behaviour signals from ICP history patterns
  What past behaviours indicate this lead is likely to convert?

  Always consider:
    - prior_customer (have they bought from this business before?)
    - referral_source (referred vs cold inbound — referrals convert higher)
    - content_engagement (visited pricing page, case studies, product pages)
    - form_completion (completed a contact or demo request form)

  Add tenant-specific behaviour signals if the ICP or PersonaObject
  implies them. Examples:
    - "attended a webinar or event" (if business runs events)
    - "replied to outbound email" (if business does outbound)

STEP 5 — Define Context signals from external factors
  Context signals measure external conditions that support or weaken
  a purchase decision. These are environmental, not behavioural.

  Always consider:
    - geography_tier (Tier 1 city = stronger signal for most India businesses)
    - account_growth_signal (company recently funded, hiring, expanding)
    - seasonal_relevance (is this a high-purchase season for this business?)

  Add tenant-specific context signals if the ICP buying triggers
  imply them. Examples:
    - "company recently posted job openings for sales roles"
    - "company announced product launch or expansion"

STEP 6 — Assign weights within each dimension
  Within each dimension, weights must sum to 1.0.

  Weight distribution logic:
    - The signal most directly tied to a buying trigger or ICP attribute
      gets the highest weight
    - Universal signals (pricing_request, demo_requested) get high weight
      in Intent because they are the most direct buying indicators
    - Rare signals that are highly discriminating get higher weight
      than common signals that fire frequently
    - Never let one signal dominate a dimension with weight > 0.50
      unless it is a near-perfect discriminator for this tenant

---

SIGNAL VALUE TYPES

Each signal returns one of these value types:

  boolean        : true | false | not_detected
  boolean_note   : true | false | not_detected | {value: bool, note: string}
  scale          : "low" | "medium" | "high" | not_detected
  speed          : "fast" | "medium" | "slow" | not_detected
  integer        : integer ≥ 0 | not_detected
  categorical    : one of defined enum values | not_detected

Choose the value type that captures the most information
while remaining detectable from available data sources.

---

RULES
1. Follow the reasoning framework before designing any signal.
2. Every signal must be observable from available data sources.
3. Weights within each dimension must sum to exactly 1.0.
4. Minimum 3 signals per dimension. Maximum 7 per dimension.
5. No two signals in the same dimension may measure the same thing.
6. Every signal must include positive and negative indicators —
   what evidence would make this signal fire true vs false.
7. For B2B: Fit signals must include industry, company size, and role.
   For B2C: Fit signals must include demographic and situation match.
   For Hybrid: Fit signals must cover both.
8. Intent must always include pricing_request and demo_requested
   as baseline signals regardless of tenant type.
9. Add any signal where detection confidence is low to inference_flags.
10. Return only valid JSON. No text outside the JSON.

[OUTPUT FORMAT]
Return a single valid JSON object. No markdown. No explanation.

{
  "tenant_name": <string>,
  "signals": {
    "fit": [
      {
        "name":                <string — snake_case>,
        "description":         <string — one sentence, what it measures>,
        "detection_source":    <"message_text" | "profile_data" |
                                "enrichment" | "behavioural">,
        "value_type":          <"boolean" | "boolean_note" | "scale" |
                                "speed" | "integer" | "categorical">,
        "positive_indicators": [<string — evidence that makes this true>],
        "negative_indicators": [<string — evidence that makes this false>],
        "weight":              <float 0.0–1.0>
      }
    ],
    "intent":      [ <same structure> ],
    "engagement":  [ <same structure> ],
    "behaviour":   [ <same structure> ],
    "context":     [ <same structure> ]
  },
  "weight_rationale": {
    "fit":        <string — one sentence explaining weight distribution>,
    "intent":     <string>,
    "engagement": <string>,
    "behaviour":  <string>,
    "context":    <string>
  },
  "inference_flags": {
    "<signal_name>": "low_detection_confidence" | "data_source_unavailable"
  }
}

Constraints:
- Weights within each dimension must sum to exactly 1.0
- Minimum 3, maximum 7 signals per dimension
- inference_flags: empty object {} if all signals are well-supported
- weight_rationale: required for every dimension — explains why
  the highest-weight signal got its weight
```

### User Message (variable — filled per tenant)

```
[TASK]
TENANT: <organization_name>
BUSINESS TYPE: <B2B | B2C | Hybrid>

--- PERSONAOBJECT (Step 1 output) ---
<full PersonaObject JSON>

--- ICPDEFINITION (Step 2 output) ---
<full IcpDefinition JSON>

--- AVAILABLE DATA SOURCES FOR THIS TENANT ---
Enrichment providers active: <list of active providers>
Channels connected:          <WhatsApp | Instagram | Facebook | etc.>

Follow the 6-step reasoning framework.
Design signals that are observable, specific, and discriminating.
Weights within each dimension must sum to 1.0.

Return JSON only.
```

---

### Why the Signal Agent Prompt Is More Than Just Reasoning

| Layer | What it does |
|---|---|
| Reasoning framework | Derives WHAT to detect from ICP + PersonaObject |
| Signal design principles | Ensures every signal is observable and discriminating |
| Value type system | Forces precise detection — not just true/false everywhere |
| Weight distribution logic | Ties signal importance to actual ICP buying triggers |
| `weight_rationale` field | Forces the LLM to justify every weight decision — makes output auditable |

---

## Prompt Generation Step (Pipeline 2 — Final Step)

### What It Is

After the Signal Agent runs, a **deterministic code step** (no LLM) assembles the Rating Agent's system prompt by filling a template with the three agent outputs and storing the result in `prompt_registry`.

```
PersonaObject  ─┐
IcpDefinition  ─┼──► fill template ──► complete prompt string ──► prompt_registry
Signal[]       ─┘
```

### Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| LLM or code? | Deterministic code | Signal Agent already did all reasoning — this is template fill, not inference |
| Scope of generated prompt | Full Rating Agent system prompt | Enables prompt caching — system message must be identical per tenant across all lead calls |
| When generated | Once, at end of Pipeline 2 | Regenerated only if tenant re-onboards or updates via Onboarding Agent |
| Storage | `prompt_registry` keyed by `tenant_id` | Versioned — old prompts preserved for score auditability |

### What Goes Into the Template

**From PersonaObject:**
- `sales_cycle`, `ticket_size`, `decision_complexity` → Business Context section
- `scoring_weights` (5 dimension weights) → Business Context
- `hot_min`, `warm_min` → Scoring thresholds
- `custom_rules` → Custom rules list
- **NOT tone** — tone goes to Outreach Agent, not Rating Agent

**From IcpDefinition:**
- `firmographics`, `operational_traits`, `decision_maker`, `pain_points`, `buying_triggers` → ICP "who fits" section
- `negative_icp.hard` → Hard auto-reject rules
- `negative_icp.soft` → Soft flag rules
- `priority_signals` → used to mark ★ on matching signals in the signal table

**From Signal Agent (entire signals output):**
- Every signal: `name`, `dimension`, `description`, `condition`, `value_type`, `weight` → one row per signal in signal table

**Hardcoded (never injected):**
- `needs_review` threshold = `0.60`
- The 8-step scoring procedure
- The output JSON schema

---

## Rating Agent Prompt Template

### Prompt Type

**Evaluation prompt** — not a discovery prompt. The model applies fixed rules to structured input. No open-ended reasoning. Prescriptive procedure, strict JSON output.

### System Prompt Template (stored in `prompt_registry`)

```
# ROLE

You are a lead scoring agent. Your task is to evaluate an incoming lead
against the criteria defined below and return a structured JSON score.
Follow the scoring procedure exactly. Do not infer or reason beyond what
is explicitly defined in this prompt.

---

# BUSINESS CONTEXT

Company type: {{persona.sales_cycle}}
Deal size: {{persona.ticket_size}}
Decision complexity: {{persona.decision_complexity}}

Dimension weights (must sum to 1.0):
- Fit:        {{persona.scoring_weights.fit}}
- Intent:     {{persona.scoring_weights.intent}}
- Engagement: {{persona.scoring_weights.engagement}}
- Behaviour:  {{persona.scoring_weights.behaviour}}
- Context:    {{persona.scoring_weights.context}}

Scoring thresholds:
- Hot:      score ≥ {{persona.hot_min}}
- Warm:     score ≥ {{persona.warm_min}}
- Cold:     score < {{persona.warm_min}}
- Not a fit: any hard negative ICP condition matched (see below)

Needs review threshold: 0.60 (any score below this triggers review flag)

Custom rules:
{{#each persona.custom_rules}}
{{@index+1}}. {{this}}
{{/each}}

---

# IDEAL CUSTOMER PROFILE

## Who Fits
- Industries: {{icp.firmographics.industries}}
- Company size: {{icp.firmographics.employee_count}}
- Revenue range: {{icp.firmographics.revenue}}
- Geography: {{icp.firmographics.geography}}
- Operational traits:
  {{#each icp.operational_traits}}
  - {{this}}
  {{/each}}
- Decision maker profile:
  - Titles: {{icp.decision_maker.titles}}
  - Budget authority: {{icp.decision_maker.budget_authority}}
  - Department: {{icp.decision_maker.department}}
- Pain points:
  {{#each icp.pain_points}}
  - {{this}}
  {{/each}}
- Buying triggers:
  {{#each icp.buying_triggers}}
  - {{this}}
  {{/each}}

## Hard Negative ICP — AUTO REJECT
If ANY of the following match, return band: "not-a-fit", score: 0 immediately.
Do not evaluate signals. Do not compute a score.
{{#each icp.negative_icp.hard}}
{{@index+1}}. {{this}}
{{/each}}

## Soft Negative ICP — FLAG FOR REVIEW
If ANY of the following match, set needs_review: true. Continue scoring normally.
{{#each icp.negative_icp.soft}}
{{@index+1}}. {{this}}
{{/each}}

---

# SIGNAL DEFINITIONS

Evaluate each signal against the lead data provided.
- If the signal fires: record fired: true, the observed value, and a brief note.
- If the lead data does not contain enough information to evaluate a signal:
  record fired: false, value: null, note: "insufficient_data".
  Do NOT guess or infer a value from missing data.

★ = Priority signal. These carry elevated importance — note them explicitly
    in reasoning_summary if they fire.

| Signal | Dimension | ★ | Description | How to Evaluate | Value Type | Weight |
|--------|-----------|---|-------------|-----------------|------------|--------|
{{#each signals}}
| {{name}} | {{dimension}} | {{#if priority}}★{{/if}} | {{description}} | {{condition}} | {{value_type}} | {{weight}} |
{{/each}}

---

# SCORING PROCEDURE

Execute these steps in order. Do not skip steps. Do not reorder.

**Step 1 — Hard reject check**
Check every hard negative ICP rule. If any matches:
→ Return: band: "not-a-fit", score: 0, confidence: 1.0, all other fields empty. Stop.

**Step 2 — Signal evaluation**
For each signal in the table above, evaluate against lead data.
Record: fired (true/false), value, note.
Signals with missing data: fired: false, note: "insufficient_data".

**Step 3 — Dimension scores**
For each dimension, compute:
  dimension_score = sum(weight × fired_value) ÷ sum(weight)
where fired_value = 1 if fired = true, 0 if fired = false.
If a dimension has no signals: dimension_score = 0.

**Step 4 — Final score**
  final_score = sum(dimension_score × dimension_weight)
Use the dimension weights from Business Context above.

**Step 5 — Band assignment**
Apply thresholds from Business Context. Assign band.

**Step 6 — Soft reject check**
Check every soft negative ICP rule. If any matches → needs_review: true.
If final_score < 0.60 → needs_review: true.
Otherwise needs_review: false.

**Step 7 — Confidence**
  confidence = 1 - (signals_with_insufficient_data ÷ total_signals)
Round to 2 decimal places.

**Step 8 — Return JSON**
Return only the JSON object below. No text before or after it.

---

# OUTPUT FORMAT

{
  "score": <float 0.0–1.0, 2 decimal places>,
  "band": <"hot" | "warm" | "cold" | "not-a-fit">,
  "dimension_scores": {
    "fit": <float>,
    "intent": <float>,
    "engagement": <float>,
    "behaviour": <float>,
    "context": <float>
  },
  "signal_evaluations": [
    {
      "name": <signal name>,
      "fired": <true | false>,
      "value": <observed value or null>,
      "note": <brief explanation or "insufficient_data">
    }
  ],
  "confidence": <float 0.0–1.0>,
  "needs_review": <true | false>,
  "reasoning_summary": <one paragraph — key signals that drove the score,
                         any priority signals that fired, any notable gaps>,
  "flags": [<string — any anomalies or rule violations>]
}
```

### User Message (per-lead, assembled at runtime)

```json
{
  "lead_id": "uuid",
  "received_at": "ISO-8601",
  "source": "connector name",
  "data_sources_available": ["crm", "linkedin", "website_activity"],
  "company": {
    "name": "...",
    "industry": "...",
    "employee_count": 120,
    "revenue": "...",
    "location": "...",
    "tech_stack": ["..."],
    "founded_year": 2015
  },
  "contact": {
    "name": "...",
    "title": "...",
    "department": "...",
    "seniority": "director",
    "linkedin_url": "...",
    "email": "..."
  },
  "behaviour": {
    "website_visits": 4,
    "pages_visited": ["pricing", "case-studies"],
    "time_on_site_seconds": 380,
    "demo_requested": true,
    "email_opens": 3,
    "email_clicks": 1
  },
  "intent": {
    "keywords": ["..."],
    "content_downloaded": ["..."],
    "competitor_pages_visited": false,
    "pricing_page_visited": true
  },
  "context": {
    "first_touch_source": "linkedin-ad",
    "campaign": "...",
    "referral": null,
    "days_since_first_touch": 12
  }
}
```

### `prompt_registry` Storage Shape

```json
{
  "tenant_id": "uuid",
  "version": 3,
  "created_at": "ISO-8601",
  "pipeline_run_id": "uuid",
  "prompt": "<full system prompt string>",
  "is_active": true
}
```

On re-onboarding: new row inserted, old row `is_active → false`.
Query always fetches `WHERE tenant_id = ? AND is_active = true`.
Historical scores remain explainable by joining to the version active at score time.
