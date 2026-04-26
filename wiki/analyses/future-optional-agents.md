---
type: analysis
question: "What future agents should be designed as extensions to the MVP minimal agent set?"
date: 2026-04-26
tags: [agents, future, recommendation-agent, workflow-agent, extensions, post-mvp, minimal-agent-set]
sources_consulted:
  - "[[analyses/persona-agent-spec]]"
  - "[[analyses/rating-agent-spec]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/scoring-quality-metrics]]"
  - "[[analyses/governance-observability-layer]]"
  - "[[concepts/action-sla]]"
  - "[[concepts/score-decay]]"
status: COMPLETE
---

# Future Optional Agents

**Context:** The MVP minimal agent set has exactly two agents — the Persona Agent (builds tenant scoring configuration) and the Rating Agent (scores each lead). These two agents are sufficient to deliver the system's core value: scored, bucketed, ranked leads delivered to salespeople in the chat interface.

This document defines two future agents — the **Recommendation Agent** and the **Workflow Agent** — as planned extensions that enhance the system's value without blocking MVP delivery. Neither is a prerequisite for the other, and neither blocks any MVP feature.

**Rule for future agents:** An agent is worth designing when:
1. The gap it fills cannot be closed by a deterministic AUTOMATION step
2. Real data or user behavior must first exist to validate the agent's judgment
3. The cost-to-value ratio is favorable compared to what AUTOMATION alone can provide

Both agents below meet these criteria — but only after MVP is operational and producing data.

---

## What the MVP Agents Deliberately Leave Out

Before defining the future agents, it is worth being explicit about what the MVP minimal set intentionally does not do — and why.

| Gap | MVP approach | Why this is acceptable at MVP |
|---|---|---|
| Personalized outreach recommendations | Rating Agent returns a single `recommended_action` string (e.g., "Call today — high intent, strong fit") | No historical data exists yet to personalize. Generic action is better than fabricated personalization. |
| Talking points tailored to specific signals that fired | Not provided | Salesperson sees the sub_score breakdown and can derive talking points themselves |
| Optimal contact channel per lead | Not provided | Channel preference requires behavioral data (which channel produced responses historically) |
| Automated follow-up sequencing for non-responsive leads | Score decay + SLA tracker handle temporal enforcement deterministically | Automated sequencing requires understanding what "works" for this tenant's leads — no data at MVP |
| Dynamic re-scoring triggers based on lead activity patterns | Explicit manual triggers (webhook on new activity, scheduled re-run) | Dynamic triggers require baseline activity patterns to avoid noise |

These gaps are real. They are intentionally deferred — not forgotten.

---

## Agent 1 — Recommendation Agent

### What Gap It Fills

The Rating Agent's `recommended_action` field is one sentence. It is accurate but generic. It tells the salesperson what category of action to take (call now, warm outreach, nurture) but not *how* to approach this specific lead.

The Recommendation Agent fills the gap between "what to do" and "how to do it for this lead specifically." It reads the full scoring context — which signals fired, how the lead has behaved, what the ICP profile says — and generates a personalized recommendation package.

**Examples of what generic vs personalized looks like:**

| Rating Agent output (MVP) | Recommendation Agent output (future) |
|---|---|
| "Call today — high intent, strong fit" | "Call today. Lead asked for pricing twice — lead with ROI framing (they're comparing costs). They're in procurement at a 200-person company, so reference your enterprise tier. Timing: business hours, likely Tue–Thu based on message activity patterns." |
| "Warm outreach — moderate intent" | "WhatsApp outreach preferred (3 of 4 interactions were on WhatsApp). Lead engaged with the pricing page but hasn't asked questions — send the case study for their industry segment first. Follow up in 48h if no response." |

### Inputs

| Input | Type | Source |
|---|---|---|
| `scoring_output` | ScoringOutput | Rating Agent |
| `lead` | EnrichedLead | Post-normalisation lead record |
| `persona` | PersonaObject | Persona Engine |
| `fired_signals` | dict | Signal extraction output (which signals were positive, which were absent) |
| `touchpoint_history` | list[Touchpoint] | Returning/rescore leads only |
| `historical_patterns` | object | Quality metrics + conversion outcomes — **requires Month 1+ data** |
| `salesperson_profile` | object (optional) | Salesperson's historical response rates, preferred language style |

### Outputs

```json
{
  "outreach_message": "string — personalized first message draft",
  "talking_points": ["string", "string", "string"],
  "recommended_channel": "call | whatsapp | email",
  "recommended_timing": {
    "window": "string",
    "urgency": "immediate | within_24h | within_48h"
  },
  "signal_rationale": {
    "signal_name": "why this signal drove this recommendation"
  },
  "confidence": "high | medium | low"
}
```

### Why It Is Not MVP

1. **Requires historical data.** The `talking_points` and `recommended_channel` are only meaningful if the system has observed what actually produced responses from similar leads. Without this, the Recommendation Agent is fabricating personalization — which is worse than a generic recommendation because the salesperson may trust it.

2. **Adds LLM cost per lead.** The Recommendation Agent is a second LLM call, after the Rating Agent. At MVP with a small tenant base, this doubles LLM cost per lead for an output that cannot yet be validated.

3. **No ground truth for recommendation quality.** The Rating Agent's output can be validated via AP1 (Bucket Outcome Rate) and AR2 (Action Rate by Bucket). There is no equivalent metric for recommendation quality until salespeople are using the system and conversion patterns are observable.

4. **Risk of hallucinated personalization.** An LLM generating "personalized" recommendations without real calibration data will produce plausible-sounding but uncalibrated advice. This can harm trust more than it builds it.

### Unlock Conditions — When to Introduce

All of these must be true before introducing the Recommendation Agent:

| Condition | Metric to check |
|---|---|
| At least 3 months of lead scoring data | Minimum data volume for pattern learning |
| AP1 (Bucket Outcome Rate) is stable and differentiated across buckets | Scoring is working — personalization now adds marginal value |
| AR2 (Action Rate by Bucket) shows channel-specific patterns | Enough salesperson behavior data to ground channel recommendations |
| AR3 (Time-to-Action Distribution) shows timing patterns | Enough temporal data to ground timing recommendations |
| CRM outcome data is connected | Conversion outcomes (responded / meeting / deal) are flowing into the system |

**Recommended introduction:** Introduce as an opt-in feature for one tenant first. Run A/B against the generic `recommended_action` baseline. Measure whether AR1 (SLA Compliance Rate) and AR2 improve. Graduate to all tenants only after the lift is confirmed.

### Design Constraints (for when it is built)

- Must not replace `recommended_action` in ScoringOutput — the Rating Agent stays simple. The Recommendation Agent produces a separate enrichment object added to the delivery package.
- Must be invokable independently of the Rating Agent — the scoring result is already persisted when the Recommendation Agent runs. If it fails, the lead is still delivered with the generic `recommended_action`.
- Must have its own lineage record so its recommendations are attributable and auditable separately from scoring.
- Must respect the "system proposes, human approves" principle — recommendations are suggestions, not instructions.

---

## Agent 2 — Workflow Agent

### What Gap It Fills

The current system handles lead lifecycle through deterministic rules: SLA Tracker fires alerts on breach, Score Decay reduces scores on inactivity, feedback triggers a re-scoring proposal. These are AUTOMATION steps — they operate on fixed rules regardless of context.

The Workflow Agent adds judgment to lifecycle decisions. Instead of "score decays by −10 after 7 days" (a fixed rule), the Workflow Agent asks: "Given this lead's profile, their interaction history, the salesperson's current workload, and patterns from similar leads — what is the right next action for this lead right now?"

**Examples of what the Workflow Agent would decide:**

| Situation | AUTOMATION (current) | Workflow Agent (future) |
|---|---|---|
| HOT lead, SLA breached by 4 hours | Alert fires | Alert fires + "This lead matches your top 3 converters from last quarter. Recommend calling within the next 2 hours specifically — they've been active on WhatsApp this morning." |
| WARM lead, 5 days no activity | Score decays by −10 | "This lead visited the pricing page again yesterday — hold decay, re-score with returning variant. Their engagement is picking up." |
| COLD lead, no response in 21 days | Decay continues toward auto-COLD | "Similar leads from this campaign converted at 18% when contacted after 3 weeks with the case study approach. Recommend one more targeted outreach before archiving." |
| WARM lead re-engaged after COLD period | Not handled explicitly | "Lead re-engaged — re-score with rescore variant immediately. Their previous cold exit was due to timing, not fit." |

### Inputs

| Input | Type | Source |
|---|---|---|
| `lead_record` | Full lead with pipeline history | Data Layer (via orchestrator) |
| `current_pipeline_stage` | string | `leads.pipeline_stage` |
| `sla_status` | object | SLA Tracker |
| `last_interaction` | timestamp | Interaction history |
| `feedback_record` | object (if any) | Feedback Collector |
| `decay_state` | object | Score Decay job state |
| `tenant_workflow_config` | object | Tenant-configured workflow preferences |
| `comparable_lead_patterns` | object | Historical patterns from similar leads — **requires data** |

### Outputs

```json
{
  "decision": "rescore | escalate | hold_decay | initiate_nurture | archive | request_human_decision",
  "rationale": "string — why this decision",
  "urgency": "immediate | scheduled | low_priority",
  "scheduled_at": "ISO-8601 or null",
  "notify_salesperson": true,
  "notification_message": "string",
  "proposed_action_for_approval": "string or null"
}
```

**Note on `proposed_action_for_approval`:** Any Workflow Agent decision that modifies the lead's scoring or routing must route through the "system proposes, human approves" principle. `[LOCKED]` The Workflow Agent can decide and notify, but the salesperson or team lead confirms before execution.

### Why It Is Not MVP

1. **Requires understanding of what "correct" workflow looks like.** The Workflow Agent must reason about what a good workflow decision looks like for this tenant's specific business. At MVP, this understanding does not exist yet. The deterministic decay and SLA rules are good enough placeholders — they encode defensible defaults.

2. **High risk of conflicting with "system proposes, human approves."** A Workflow Agent that makes lifecycle decisions (re-score, escalate, archive) is operating in territory where wrong decisions have real cost. Without calibration data and established patterns, the agent will produce errors that erode salesperson trust faster than they build it.

3. **Orchestration complexity.** The Workflow Agent would need to co-exist with the SLA Tracker, Score Decay Job, and Feedback Collector — all of which currently run independently. Introducing an agent that can override or suspend these jobs adds significant state management complexity that is not appropriate for MVP.

4. **Not blocked by the current architecture.** The AUTOMATION steps (SLA Tracker, Score Decay) can run indefinitely at MVP without creating technical debt. They can be replaced or augmented by the Workflow Agent later without requiring a rewrite. There is no urgency.

### Unlock Conditions — When to Introduce

| Condition | What it validates |
|---|---|
| System stable for 3+ months | Orchestration infrastructure is proven before adding agent-level lifecycle decisions |
| AR1 (SLA Compliance Rate) baseline established | Know what "normal" SLA behavior looks like before optimizing it |
| AP1 shows clear bucket outcome differentiation | Scoring is reliable enough that workflow decisions based on buckets are meaningful |
| Tenant workflow patterns documented | The team understands how salespeople actually use the system day-to-day |
| "System proposes, human approves" infrastructure proven | The approval flow must be reliable before adding more proposals to it |

**Recommended introduction:** Start with a narrow scope — re-score trigger decisions only (when should a lead be re-scored, vs. letting decay continue?). Validate against the manual re-score patterns from the first 3 months. Graduate to broader lifecycle decisions only after the narrow scope is validated.

### Design Constraints (for when it is built)

- Must never make irreversible decisions autonomously. Archiving, escalating, or modifying a lead's score must go through the approval flow.
- Must be interruptible. If a salesperson manually acts on a lead while the Workflow Agent is processing it, the agent's output is discarded.
- Must write to lineage. Every Workflow Agent decision must be a lineage record so it is auditable and attributable.
- Must degrade gracefully. If the Workflow Agent is unavailable, the AUTOMATION fallbacks (SLA Tracker, Score Decay) continue running unchanged.

---

## What Is Explicitly NOT a Future Agent

Not every enhancement requires an LLM agent. These capabilities should remain AUTOMATION regardless of system maturity:

| Capability | Why it should stay AUTOMATION |
|---|---|
| Lead deduplication | Deterministic matching rules (phone → email → name+location) are correct and debuggable. LLM deduplication introduces non-reproducible results. |
| Signal extraction from lead data | Must stay deterministic for cost control (1 LLM call per lead) and debuggability. An "enrichment agent" that uses LLM for extraction would break the fundamental architecture. |
| Bucket threshold enforcement | Tenant-configured numbers. Rule application is deterministic. Adding LLM judgment to "should this lead be HOT?" contradicts the structured scoring purpose of the Rating Agent. |
| Disqualification rule application | Explicit per-tenant business rules. LLM application adds cost and inconsistency without benefit. |
| Quality metrics computation | SQL aggregations against defined fields. Deterministic by design — the metrics must be reproducible for the feedback loop to be credible. |
| Report generation | Templated aggregations from quality_snapshots. If narrative interpretation is needed, it is a presentation layer concern, not an agent. |

---

## Principles for Future Agent Expansion

When considering whether to introduce a new agent beyond the Recommendation and Workflow Agents, apply these tests:

**1. Data prerequisite test.** Does the agent need real operational data to produce non-fabricated output? If yes, identify the specific metric or data volume threshold that unlocks it.

**2. Determinism test.** Could a well-designed rule or SQL query produce the same output? If yes, build the rule first and validate whether the LLM actually improves on it.

**3. Cost proportionality test.** Does the value added justify an additional LLM call per lead (or per tenant event)? LLM calls have a hard cost floor. The output must be measurably better than AUTOMATION alternatives.

**4. Oversight test.** If the agent makes an error, is the error visible and correctable before it causes downstream harm? Agents operating in the critical scoring path (Pipeline 1) face a higher bar than agents in post-delivery enrichment.

**5. Minimal set test.** Could the proposed agent's responsibilities be absorbed by an existing agent? Before introducing a third agent, verify that Persona Agent and Rating Agent genuinely cannot cover the use case.

---

## Summary: Full Agent Set Over Time

| Phase | Agent set | What's added |
|---|---|---|
| **MVP** | Persona Agent + Rating Agent | Core: tenant setup + lead scoring |
| **Month 3–6** | + Recommendation Agent (opt-in) | Personalized outreach guidance; A/B validated |
| **Month 6–12** | + Workflow Agent (narrow scope) | Re-score trigger judgment; approval-gated |
| **Future** | Workflow Agent (full scope) | Full lead lifecycle orchestration; fully validated |

The two MVP agents are sufficient to deliver the product's core value. Every future agent is an enhancement of that value — not a correction of a missing piece.

---

## Related Documents

- [[analyses/persona-agent-spec]] — MVP Agent 1 full specification
- [[analyses/rating-agent-spec]] — MVP Agent 2 full specification
- [[analyses/execution-type-classification]] — full workflow step classification including future agent insertion points
- [[analyses/delivery-integration-layer]] — Recommendation Agent output would be added to the delivery package
- [[concepts/action-sla]] — Workflow Agent would eventually augment (not replace) SLA enforcement
- [[concepts/score-decay]] — Workflow Agent would eventually augment (not replace) decay rules
- [[analyses/scoring-quality-metrics]] — unlock conditions for both future agents reference specific metrics
