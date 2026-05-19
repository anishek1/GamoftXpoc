---
type: analysis
question: "What are the 3 core use cases the platform must support for initial launch, with explicit inputs, outputs, and stakeholders?"
date: 2026-05-19
tags: [use-cases, mvp, b2b, b2c, smb, noise, pipeline1, onboarding, stakeholders]
sources_consulted:
  - "[[analyses/global-data-collection-architecture]]"
  - "[[analyses/orchestration-layer-spec]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/mvp-scope-sign-off]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/onboarding-flow-stage-map]]"
status: COMPLETE
---

# Core Use Cases — MVP Launch

**Question:** What are the 3 core use cases the platform must support for initial launch, with explicit inputs, outputs, and stakeholders?
**Date:** 2026-05-19

---

## Plain-English Summary

**Why this exists:** The Lead Intelligence Engine must handle three qualitatively different types of incoming leads. Each represents a distinct path through Pipeline 1, a different enrichment outcome, and a different stakeholder action. This page maps those three paths end-to-end so all parties — engineering, product, and sales — share the same mental model of what the system does and for whom.

**The three cases are:**
1. **High-Intent B2B Lead** — a verifiable business buyer with an explicit signal → HOT outcome, immediate salesperson action required
2. **SMB / Fragmented Lead** — a real buyer whose company cannot be officially verified → COLD outcome, salesperson qualification prompt
3. **Low-Signal / Noise Message** — a message with no processable intent signal → pipeline stops early, no enrichment, no salesperson burden

---

## Use Case 1 — High-Intent B2B Lead (Enterprise, Verified)

### Description
A decision-maker at a verifiable company sends a message expressing clear buying intent. The system has sufficient data to produce a high-confidence score. The salesperson receives a HOT card and must follow up within 24 hours.

### Trigger
A WhatsApp DM, Instagram DM, Facebook message, or Lead Ad form submission arrives from a lead whose company is identifiable and whose message contains explicit or implicit buying intent.

### Inputs

| Input | Source | Example |
|---|---|---|
| Raw message text | WhatsApp / Instagram / LinkedIn | "Hi, I'm James Whitfield, CTO at Barclays. We're evaluating enterprise vendors for our data platform." |
| Channel phone/PSID/IGSID | Platform webhook | `+91-98XXXXXXXX` (WhatsApp), IGSID (Instagram) |
| Lead form fields (if Lead Ad) | Facebook/Instagram Lead Ads | `{ full_name, company_name, job_title, phone }` |
| Tenant persona + ICP | Pipeline 2 output (pre-built) | Gamoft B2B persona: targets enterprise tech/finance, decision-maker roles |
| Tenant signal definitions | Pipeline 2 output (pre-built) | Signals: `pricing_request`, `demo_requested`, `urgency_language`, `role_relevance`, etc. |

### Process (Pipeline 1 Steps)

1. **Conversation thread check** — new thread confirmed
2. **Message Parser (Haiku)** — extracts: `name`, `company`, `role`, `intent_text`, `proceed: true`
3. **Free Signal Scorer** — company name + role title → B2B confirmed; no identity API needed
4. **Jurisdiction Classifier** — phone prefix → `country_code: GB` or `IN`
5. **Company Disambiguator** — Apollo search returns one high-confidence match
6. **Company Resolver** — Apollo + Companies House (UK) or Apollo + MCA21 (India) → full company profile
7. **Person Resolver** — Apollo person search → role, tenure, identity verified against phone
8. **Consent Gate** — tenant consent policy allows enrichment for this jurisdiction
9. **Intent Gate** — `intent_specificity: HIGH` → no clarification needed, score immediately
10. **Scoring Agent (Sonnet)** — evaluates across 5 dimensions with full enriched context

### Outputs

| Output | Value | Destination |
|---|---|---|
| Score | 80–100 | `leads` table, `scored_leads` view |
| Bucket | HOT | Lead card in salesperson chat interface |
| Reasoning | "CTO of a large verifiable company with explicit vendor evaluation intent" | Lead card |
| `lead_completeness` | 0.85–0.95 | Delivery layer; lineage_record |
| `recommended_action` | "Call today — high intent, strong fit" | Lead card |
| SLA timer | 24-hour HOT SLA | Push notification + SLA breach monitor |
| Pipeline lineage | Full trace: pipeline_run + task_execution + lineage_record entries | Governance layer, audit log |

### Stakeholders

| Stakeholder | What they receive | When |
|---|---|---|
| **Salesperson** | HOT lead card in chat; push notification; 24-hour SLA timer | Immediately after Bucketize |
| **CRM system** | Lead record synced automatically | Same pipeline run |
| **Team lead** | HOT SLA compliance tracked in ops dashboard (AR1) | Weekly quality review |
| **Engineering lead** | Pipeline success, latency logged as OP1/OP2 KPIs | Per-run |

### Success Criteria
- Lead card appears in salesperson UI within 120 seconds of message arrival (OP1 target)
- Score ≥ 80, bucket = HOT, `recommended_action` populated
- Push notification delivered
- 24-hour SLA timer started

---

## Use Case 2 — SMB / Fragmented Lead (Real Buyer, Unverifiable Company)

### Description
A genuine business buyer contacts the tenant, but the company they represent is a small or informal business not registered in any searchable database. The system cannot verify the company, resulting in low `lead_completeness`. The pipeline still produces a score, but it is COLD due to missing data — not because the person is a bad prospect. The salesperson receives a COLD card with a specific qualification prompt that, if acted on, can upgrade the lead.

### Trigger
A WhatsApp or Instagram DM arrives from a person who identifies as a business owner or buyer but whose company cannot be found through any enrichment source.

### Inputs

| Input | Source | Example |
|---|---|---|
| Raw message text | WhatsApp DM | "I am Sunita Sharma, I run a small catering business in Lucknow and I want to order supplies in bulk" |
| Channel phone number | WhatsApp webhook | `+91-97XXXXXXXX` |
| Tenant persona + ICP | Pipeline 2 output | Gamoft B2B persona (or Urvee Organics B2C persona, if applicable) |
| Tenant signal definitions | Pipeline 2 output | Signals: `bulk_order_intent`, `business_ownership_indicator`, `role_relevance`, etc. |

### Process (Pipeline 1 Steps)

1. **Message Parser (Haiku)** — extracts: `name: "Sunita Sharma"`, `company: null`, `business_ownership: true`, `intent_text: "order supplies in bulk"`, `proceed: true`
2. **Free Signal Scorer** — `business_ownership: true` (+3 B2B) + "bulk order" intent (+3 B2B) → B2B confirmed despite no company name
3. **Jurisdiction Classifier** — `+91` → India (IN)
4. **Company Resolver** — Apollo: no match; MCA21: 200+ partial matches, no reliable result; GST Portal: no GSTIN available
5. **Company data result** — `company_verified: false`, `lead_completeness: 0.38`, note: "Company details could not be verified — small business below registry threshold"
6. **Consent Gate** — passes (India DPDP tenant config in place)
7. **Intent Gate** — `intent_specificity: medium` → no clarification sent; score with available data
8. **Scoring Agent (Sonnet)** — evaluates with confirmed B2B intent but thin company profile

### Outputs

| Output | Value | Destination |
|---|---|---|
| Score | 35–50 | `leads` table |
| Bucket | COLD | Lead card with qualification flag |
| Reasoning | "Verified business buyer with clear bulk purchase intent; company details unverifiable — enrichment inconclusive" | Lead card |
| `lead_completeness` | 0.30–0.45 | Routed to `needs_review` path if below 0.50 threshold |
| `recommended_action` | "Qualify in conversation: ask for GST number or business name to verify" | Lead card |
| Qualification note | "Ask for GST number or formal business name to improve score" | Visible to salesperson on card |
| Pipeline lineage | Full trace | Governance layer |

### Stakeholders

| Stakeholder | What they receive | When |
|---|---|---|
| **Salesperson** | COLD lead card; qualification prompt; note explaining what data is missing | After Bucketize |
| **Team lead** | COLD card with explicit action suggestion — not a discard | After Bucketize |
| **Product owner** | `lead_completeness` distribution per run tracked as per-run quality metric | Per-run quality snapshot |
| **Engineering lead** | Enrichment provider failure (Apollo/MCA miss) logged in task_execution | Per-run |

### Upgrade Path
If the salesperson asks for the GST number in conversation and the lead provides it → the pipeline re-runs with the GST data → company verified → `lead_completeness` jumps → score upgrades to WARM or HOT. This is a live re-score, not a manual override.

### Success Criteria
- Lead still appears in salesperson UI (not silently discarded)
- COLD card shows the specific qualification question
- `lead_completeness` below threshold triggers `needs_review: true`
- Re-score path is available if salesperson provides additional data

---

## Use Case 3 — Low-Signal / Noise Message (Safe Deprioritization)

### Description
A message arrives that contains no processable signal — it is either noise (emojis, one-word greetings, misdirected replies) or a message type that the system cannot extract any lead data from. The pipeline stops at the Message Parser (Step 2), no enrichment APIs are called, no salesperson time is consumed, and the event is logged for ops visibility.

This is the "safe deprioritization" case: the system confidently discards the message without ever surfacing it to a salesperson, without burning an enrichment call, and without creating a ghost lead record.

### Trigger
Any inbound message on a connected channel that the Message Parser judges to have no extractable lead signal.

### Inputs

| Input | Source | Examples |
|---|---|---|
| Raw message text | Any channel | "hi", "ok", "hello sir please call me", "👍", misdirected replies, "wrong number" |
| Channel sender identifier | Platform webhook | Any sender |
| Tenant's active prompt config | Pipeline 2 output | Used only if pipeline reaches Scoring Agent — does not apply here |

### Process (Pipeline 1 Steps — Short Path)

1. **Conversation Thread Check** — new thread or continuation; both handled
2. **Message Parser (Haiku)** — evaluates message content:
   - No name, company, role, or intent extractable
   - Message length or content does not indicate a buying inquiry
   - Output: `proceed: false`, `discard_reason: "no extractable signal — message contains no identifiable name, company, role, or intent"`
3. **Pipeline stops** — no further steps execute; no API calls, no enrichment, no Scoring Agent call

### Outputs

| Output | Value | Destination |
|---|---|---|
| `proceed` flag | `false` | Pipeline controller |
| `discard_reason` | Human-readable string | `leads` table, `intake_event_log` |
| `pipeline_stage` | `insufficient_signal` | `leads` table |
| Lead card | **Not created** | Salesperson sees nothing |
| Lineage entry | Event logged with `discard_reason` | Governance layer, `pipeline_run` record |

### Stakeholders

| Stakeholder | What they receive | When |
|---|---|---|
| **Salesperson** | Nothing — no card, no notification | Never |
| **Ops / Engineering lead** | Discard rate tracked: if > X% of messages are being discarded, suggests connector-level spam or bot traffic | Per-run quality snapshot |
| **Team lead** | Aggregate discard rate visible in ops dashboard; spike = connector health issue | Weekly ops review |

### What Is NOT Happening
- The message is not silently dropped with no record. It is logged with a discard reason.
- The system does not create a lead record that shows up in reports with no data.
- The salesperson does not receive a blank or partial card to manually review.
- No enrichment provider is billed for this event.

### Success Criteria
- Message does not appear in salesperson UI
- Event is logged in `intake_event_log` with `discard_reason`
- `pipeline_stage = insufficient_signal` set on the discarded record
- Discard rate per run is visible in the ops dashboard

---

## Cross-Use-Case Stakeholder Map

| Stakeholder | UC1: HOT B2B | UC2: SMB Fragmented | UC3: Noise |
|---|---|---|---|
| **Salesperson** | HOT card + 24h SLA | COLD card + qualification prompt | Nothing |
| **Team lead** | HOT SLA compliance | COLD card review | Discard rate spike alert |
| **Product owner** | Scoring Lift KPI (BK4) | `lead_completeness` distribution | — |
| **Engineering lead** | OP1/OP2 latency KPIs | Enrichment miss rate | Discard event log |
| **CRM system** | Auto-synced immediately | Synced with qualification flag | Not created |

---

## Evidence

- Pipeline 1 step sequence and two entry paths (source: [[analyses/orchestration-layer-spec]] Section 4)
- Four real-world scenarios including B2B enterprise and SMB fragmented (source: [[analyses/global-data-collection-architecture]] Section 4)
- Message Parser `proceed: false` path (source: [[analyses/global-data-collection-architecture]] Section 2)
- `lead_completeness` routing and `needs_review` flag (source: [[analyses/orchestration-layer-spec]] Section 4.3 Stage 5)
- Lead card delivery and salesperson notification (source: [[analyses/delivery-integration-layer]])
- MVP scope boundaries and POC tenants (source: [[analyses/mvp-scope-sign-off]])

## Caveats & Gaps

- **Use Case 2 upgrade path** (salesperson provides GST → re-score) is architecturally supported but the exact UX trigger for re-scoring from a conversation reply is not yet specified. See open question #3 in [[analyses/global-data-collection-architecture]].
- **Discard threshold** (what percentage of messages being discarded is normal vs. a signal of connector spam) is not yet set. Logged as a per-run metric but the alert threshold is `[TBD — set after Month 1 baseline]`.
- **B2C variant of Use Case 1** (individual consumer buying for personal use, e.g. Urvee Organics customer) follows the same HOT/WARM/COLD path but uses different signal weights and B2C enrichment sources (Truecaller, Instagram profile). Not separately elaborated here; see [[analyses/adaptive-scoring-strategy-b2b-b2c]].

## Follow-up Questions
- What is the target discard rate per connected channel? (Alert threshold for UC3 ops monitoring)
- Should the upgrade path in UC2 (GST → re-score) be automatic on reply, or require the salesperson to manually trigger a re-run?
- Is there a fourth use case for the returning lead (second message from the same person/company)? [[analyses/global-data-collection-architecture]] Section 1 covers conversation threading but no separate use case card exists for it.
