---
type: analysis
question: "Document the governance and observability layer: monitoring, auditability, lineage, feedback loops, quality tracking, and security controls."
date: 2026-04-19
tags: [governance, observability, security, quality, lineage, monitoring, auditability]
sources_consulted: [sources/2026-lead-intelligence-engine-reference, raw/assets/lead_intelligence_manual_enrichment_playbook]
related: [analyses/orchestration-layer-spec, analyses/scoring-quality-metrics]
status: COMPLETE
---

# Governance and Observability Layer

**Deliverable:** Governance and Observability Layer documentation
**Audience:** S1 (data layer) and S2 (intelligence layer) developers
**Date:** 2026-04-19

---

## 1. Purpose & Position

The Governance Layer is a **cross-cutting layer** — it does not sit inside Pipeline 1 or Pipeline 2. It receives events from both pipelines continuously and runs its own independent jobs on schedule.

```
Pipeline 2 (Onboarding) ──┐
                           ├──► GOVERNANCE LAYER
Pipeline 1 (Event/Lead) ──┘
       events, lineage,
       feedback, metrics
```

**Why it is separate from both pipelines:** Governance concerns are orthogonal to execution concerns. Pipeline 1 must be fast and reliable — every millisecond of governance work added to the critical path is latency added to lead delivery. By running governance as a separate layer (event-driven and scheduled), the pipelines stay deterministic and fast, while governance gets to be thorough and independent. A governance failure never halts a pipeline run.

It is responsible for six domains, in this order of dependency:

| Domain | Section | Why this order |
|---|---|---|
| Monitoring | Section 2 | Observes pipeline runs in real time — must come first |
| Auditability | Section 3 | Records who did what and when — depends on pipeline events |
| Lineage | Section 4 | Provenance per lead per stage — depends on pipeline writes |
| Feedback Loops | Section 5 | Converts outcomes into improvement signals — depends on lineage |
| Quality Tracking | Section 6 | Computes metrics from lineage + feedback — depends on both |
| Security Controls | Section 7 | Cross-cutting constraint on all of the above |

Nothing in the governance layer is in the critical path of a pipeline run. All jobs run independently — scheduled or event-driven. **A failure in the governance layer must never halt Pipeline 1 or Pipeline 2.**

---

## 2. Monitoring

### 2.1 What Is Monitored and Why

**Why monitor at all:** The orchestrator runs deterministically, but the world it operates in is not. Channels go down. LLM agents time out. Lead volumes spike unexpectedly. Confidence distributions shift as tenant ICPs drift. Without per-run monitoring, these problems are invisible until a salesperson notices a bad recommendation. With it, the system surfaces problems automatically — before they affect output quality and before the team has to wait for a complaint to know something broke.

**Per-run (Pipeline 1) — written at end of every run:**

| Metric | Description | Why it is tracked |
|---|---|---|
| Total run duration | Wall-clock time from run start to final lead output | Detects infrastructure slowdowns and LLM latency spikes |
| Per-agent duration | Time spent in each stage (data gather, enrichment, normalise, scoring) | Isolates which stage is the bottleneck when total duration rises |
| Leads processed | Total leads in run | Baseline denominator for all rate metrics |
| Leads delivered | Reached `delivered` state | Confirms the pipeline is producing usable output |
| Leads flagged | Routed to `human_review` (confidence < 50% or scoring_failed) | High flag rate = the Scoring Agent is uncertain; needs investigation |
| Leads failed | Reached `failed` state after retries exhausted | Persistent failures mean enrichment or LLM infrastructure problems |
| Source success/failure | Per-channel: success, failure, incomplete_fetch | Identifies which channel is broken without stopping the run |
| API quota consumed | Per channel per tenant, per run | Prevents quota exhaustion from going unnoticed |
| Confidence distribution | Spread across ≥80%, 50–79%, <50% bands | A shift toward low confidence is an early signal of prompt or signal drift |
| Bucket distribution | HOT / WARM / COLD counts per run | Sudden change in distribution = lead mix changed or scoring drifted |

**Per-tenant (Pipeline 2) — written at each onboarding stage:**

| Metric | Description | Why it is tracked |
|---|---|---|
| Onboarding stage completed | persona_ready, icp_ready, signals_ready, onboarding_complete | Confirms each agent succeeded before the next depends on it |
| Agent duration | Time per Pipeline 2 LLM agent call | Slow onboarding agents signal prompt size or LLM availability issues |
| Signal count generated | How many signals Signal Agent produced per dimension | Too few signals = scoring will be imprecise; too many = prompt bloat |
| Prompt template version | Which version is active for this tenant | Needed for lineage — scores change when prompts change |

**Background jobs — written per execution:**

| Job | Metrics written | Why it matters |
|---|---|---|
| Score Decay | Leads decayed, score changes applied, leads auto-moved to COLD | Confirms decay is running on schedule; any gap means stale HOT scores |
| SLA Tracker | HOT leads breached SLA, alerts sent | SLA breaches are the most direct signal of salesperson behaviour gaps |
| Quality Tracking | Metric snapshot written to `quality_snapshots` | Confirms the quality jobs are running; a missing snapshot = missing data |

### 2.2 Where Monitoring Data Is Written

All per-run monitoring data is written to the **observability log** by the orchestrator at Phase 06 end (Pipeline 1) and at Pipeline 2 completion.

Storage: `[TBD — same Postgres vs dedicated observability table vs external tool (Grafana/Datadog)]`

### 2.3 Alerting

Alerts trigger notifications to team lead. All thresholds are `[TBD — team input required]`.

**Why thresholds are not set now:** Setting alert thresholds before baseline data exists produces arbitrary numbers. A 5% failure rate sounds bad, but for a new system processing 10 leads a run it is one lead — not actionable. After Month 1, baseline distributions are known and thresholds can be set against real data.

**Suggested alert triggers (starting point — to be calibrated after Month 1):**

| Condition | Suggested threshold | Priority | Why this threshold |
|---|---|---|---|
| Score coverage drops | < 80% leads successfully scored in a run | High | More than 20% of leads not reaching a bucket means the pipeline is losing significant volume |
| Pipeline failure rate | > 5% leads reaching `failed` state | High | Persistent failures indicate a systemic infrastructure problem, not noise |
| Human review queue | > 20% leads routed to `human_review` in a run | Medium | High flag rate = low Scoring Agent confidence; signals prompt or data quality issue |
| HOT lead SLA breach | Any HOT lead uncontacted after 24h | High | HOT leads are the highest-value output; even one breach is a direct business loss |
| Confidence distribution | > 50% leads below 50% confidence in a run | Medium | If the system is uncertain about more than half the leads, the scoring inputs are unreliable |
| All sources fail | Any run where all channels return failure | Critical | Zero leads in = zero leads out; the entire pipeline is blocked |
| Pipeline 2 failure | Any LLM agent in onboarding fails | High | A failed onboarding blocks Pipeline 1 from running for that tenant |

Alert delivery mechanism: `[TBD — chat message, email, or both]`

---

## 3. Auditability

### 3.1 Principle

Every action in the system must be traceable to: **who** triggered it, **what** happened, **when**, and **for which tenant and lead**. This is non-negotiable. `[LOCKED — source ref Sections 02, 10.5]`

**Why auditability is non-negotiable:** Lead scoring decisions affect which customers get follow-up and which do not. If a salesperson disputes a bucket assignment, the team must be able to show exactly what data went in, which signal values were extracted, which prompt version was used, and what score came out. Without this, disputes are unresolvable and the system cannot be debugged or improved.

### 3.2 Two Audit Surfaces and Why Two

**Why two surfaces, not one:** `pipeline_log` and `access_log` answer fundamentally different questions:

- `pipeline_log` answers: *What did the system do to this data?* — every transformation, every score, every signal value, every agent call.
- `access_log` answers: *What did a human do in this system?* — who viewed a lead, who exported data, who triggered a re-run.

Mixing them into one table makes it impossible to answer either cleanly. A query for "every step taken on lead X" would return both system events and user events, requiring complex filtering to separate them. Keeping them separate means each table has a single, unambiguous purpose — and each can be indexed and queried optimally for its specific access pattern.

**Surface 1 — `pipeline_log` (transformation audit):**

Records every data transformation per lead per stage across both pipelines. Written by the orchestrator after every tool call.

| Field | Description |
|---|---|
| `run_id` | Unique ID for this pipeline run |
| `lead_id` | Which lead (null for Pipeline 2 entries) |
| `agent_id` | Which component produced this entry |
| `tenant_id` | Which tenant |
| `pipeline` | `onboarding` or `lead_processing` |
| `timestamp` | When the entry was written |
| `input_snapshot` | Exact input sent to the agent |
| `output_snapshot` | Exact output the agent returned |
| `duration_ms` | Execution time |
| `prompt_version` | Active prompt version (LLM agents only, null otherwise) |
| `confidence` | Confidence at this step (null for pre-scoring stages) |
| `error` | Error string on failure, null on success |

Full schema: `[TBD from S1 — pipeline_log schema ticket]`

Immutable — entries are never updated or deleted. Append-only.

**Surface 2 — `access_log` (user action audit):**

Records every user action on the system. New table.

```sql
CREATE TABLE access_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    TEXT        NOT NULL,
  user_id      UUID        NOT NULL,
  action       TEXT        NOT NULL,
  resource_id  UUID,
  metadata     JSONB,
  timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

`action` examples: `view_lead`, `export_leads`, `submit_feedback`, `config_change`, `onboarding_trigger`, `manual_bucket_override`

`resource_id` is the `lead_id` for lead-level actions, null for system-level actions.

### 3.3 Auditability Rules `[from playbook Section 12]`

- Only record information relevant to qualification, follow-up, or account planning
- Prefer verified facts over assumptions; label inferences explicitly
- Use dated notes so the team knows how current the enrichment is
- No hard deletes — soft delete only (`deleted_at TIMESTAMPTZ NULL`)
- All updates timestamped (`created_at`, `updated_at` on every table)

---

## 4. Lineage

Lineage is the complete provenance chain for every lead from capture to delivery. It answers: *given this score, what data went in, which agent produced it, and which prompt version was used?*

Full lineage documentation is in [[analyses/orchestration-layer-spec]] Section 8.4.

**Key lineage facts:**

- Written by the orchestrator — NOT by individual tools
- Written after every tool call, every stage, both pipelines
- Stored in `pipeline_log` — same table as audit Surface 1 (one table serves both purposes)
- Concurrent writes are safe — each entry unique on `(run_id, lead_id, stage)`
- Used by the deferred Adaptive Signal Lifecycle (Add-ons 6/7/8) — it reads lineage to discover signal patterns and audit signal extraction accuracy

**Why one table serves both purposes (lineage and audit):** Both lineage and audit record the same underlying event — a tool call with an input and an output. The difference is the question asked of the data. Audit asks: *was this action legitimate?* Lineage asks: *why did this score turn out this way?* The same row answers both questions. A second table would duplicate the data and create a synchronisation risk.

**Lineage build rule `[LOCKED]`:** Build lineage BEFORE adding the second LLM agent.

**Why:** Once multiple agents run simultaneously, retrofitting an audit trail requires reconciling concurrent, interlocking state across all agents. The cost grows as roughly the square of the number of agents — each new agent adds new input/output permutations that must all be traced back through shared state. Building lineage before the second agent means adding one complexity layer at a time, not eight at once. The `pipeline_log` schema must be locked before any second agent ships.

---

## 5. Feedback Loops

### 5.1 Overview

**Why feedback loops exist:** The system scores leads based on signal definitions and weights set at onboarding. But real-world behaviour changes — a signal pattern that predicted conversion six weeks ago may no longer predict it today. Without a feedback mechanism, the system silently degrades: scores drift from reality while the engine keeps producing confident-looking numbers. Feedback loops close the cycle by converting salesperson outcomes into the training signal that tells the system where its predictions are wrong.

Feedback is a **3-step enforcement loop**: collection → attribution → pattern detection → team lead action. It runs entirely through the Governance Layer — not in either pipeline's critical path.

```
Salesperson feedback (thumbs down / not converted)
         ↓
Step 1: Attribution job (immediate)
         ↓
Step 2: Pattern detection (weekly job)
         ↓
Step 3: Team lead recommendation → human-approved action
         ↓
   ICP + Signal Agent re-run  OR  weight update  OR  prompt update
```

**Why three steps, not one:** Raw feedback alone is not actionable. A thumbs down tells you a lead was wrong — it does not tell you *why*. Attribution adds the *why* by connecting the feedback to the specific signal version, prompt version, and dimension scores that produced the wrong bucket. Pattern detection then identifies whether the *why* is a systematic problem (the same signal keeps causing errors) or noise (one bad lead). Only then does a recommendation make sense. Skipping attribution produces noise. Skipping pattern detection produces overreaction.

### 5.2 Collection — What the Salesperson Sees

One-tap per lead card in the chat interface `[LOCKED — source ref Section 11.6]`:
- **Thumbs up** — lead was correctly prioritised
- **Thumbs down** — lead was wrongly prioritised
- **Optional reason tags:** wrong timing, wrong contact, wrong product, budget
- **Outcome field:** converted / not converted (secondary tap, after thumbs)

**Why the feedback must be simple:** Salespeople are paid to sell, not to fill in forms. If the feedback mechanism requires more than two taps, usage drops. Below 20% feedback rate, pattern detection produces statistically meaningless results — the sample is too small to distinguish signal from noise.

Feedback rate alert `[LOCKED]`: if feedback rate drops below 20% of delivered leads within a window → alert team lead. Zero feedback = zero learning.

Written to `feedback_events` table:

```sql
CREATE TABLE feedback_events (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    TEXT        NOT NULL,
  lead_id      UUID        NOT NULL,
  user_id      UUID        NOT NULL,
  verdict      TEXT        NOT NULL CHECK (verdict IN ('up', 'down')),
  reason_tags  TEXT[],
  outcome      TEXT        CHECK (outcome IN ('converted', 'not_converted', NULL)),
  timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5.3 Step 1 — Attribution (Immediate, Triggered on Every Feedback Event)

**How it works:** The moment a thumbs down or "not converted" is recorded, an attribution job fires for that lead:

```
Pull all pipeline_log entries WHERE lead_id = this lead
Extract:
  signal_version      — which Signal Agent run created the signal definitions used
  prompt_version      — which prompt template was active at scoring time
  fired_signals[]     — which signals were extracted and what values they had
  dimension_scores{}  — fit / intent / engagement / behavioral / context breakdown
  explanation_reasons[]  — the 3 reasons the Scoring Agent gave for the bucket
  confidence          — how confident the system was at scoring time

Write to: attributed_feedback table
```

**Why attribution happens immediately (not in the weekly job):** The weekly pattern detection job needs attributed data to work from. If attribution were also weekly, there would be no data to pattern-detect against until two weeks had passed. Immediate attribution also means that when a team lead reviews a specific lead card, the full attribution context is already available — no waiting for a batch job.

```sql
CREATE TABLE attributed_feedback (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  feedback_id         UUID        NOT NULL,
  lead_id             UUID        NOT NULL,
  tenant_id           TEXT        NOT NULL,
  signal_version      TEXT        NOT NULL,
  prompt_version      TEXT        NOT NULL,
  fired_signals       JSONB,
  dimension_scores    JSONB,
  explanation_reasons TEXT[],
  confidence          INTEGER,
  timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Why attribution matters:** Raw thumbs down is useless. Attributed thumbs down tells you WHERE the system went wrong — was it the signal definition, the prompt, or the weight? Without attribution, the recommendation to the team lead would be "something is wrong" — with attribution, it is "signal version 2.1 appears in 7 of the 9 wrong-bucket leads this week, and `pricing_intent` fired in all 7."

### 5.4 Step 2 — Pattern Detection (Weekly Job)

**How it works:** Weekly job scans `attributed_feedback` for the past 7 days and finds correlations per tenant:

| Pattern | Question it answers |
|---|---|
| Group by `signal_version` | Which signal version appears most in wrong-bucket leads? |
| Group by `prompt_version` | Which prompt version appears most in wrong-bucket leads? |
| Group by `fired_signals` | Which signal combinations consistently produce wrong scores? |
| Group by `explanation_reasons` | Which reasons keep appearing in leads that didn't convert? |
| Group by `confidence` band | Are confident scores (≥80%) still producing wrong buckets? |

**Why weekly, not daily:** Daily pattern detection on a small tenant (20–50 leads/day) would fire on samples too small to distinguish a real pattern from random variation. A week of data produces enough volume to identify a repeating pattern with confidence. For high-volume tenants, the cadence can be shortened — but weekly is the correct starting point.

**Flagging threshold: `[TBD — team decision]`**

Recommended approach: fixed count. When N leads sharing the same signal version or prompt version receive negative feedback → flag for team lead review. Value of N: `[TBD]`.

**Why fixed count over rate:** Rate-based thresholds require knowing the total feedback volume, which is unknown before Month 1. A fixed count of N wrong-bucket leads sharing the same root cause is immediately interpretable — it either happened or it did not. Upgrade to rate-based after Month 1 when volume is known.

**Pattern detection output example:**

```
Signal version 2.1 → 7 wrong-bucket leads
  Most common fired signal: pricing_intent = true (in 6 of 7 leads)
  Most common reason: "Requested pricing twice in 48 hours"
  Confidence distribution: 5 leads were ≥80% confidence (system was sure, but wrong)

Prompt version 1.3 → 5 wrong-bucket leads (Gamoft tenant only)
```

### 5.5 Step 3 — Team Lead Recommendation (Human-Approved)

**How it works:** When a pattern crosses the flagging threshold, the system sends a structured recommendation to the **Team Lead** of the affected tenant. The team lead is a **tenant-scoped role** — Urvee's team lead sees only Urvee's patterns; Gamoft's team lead sees only Gamoft's. RLS enforces this automatically.

**Why the recommendation goes to the team lead, not the admin or the salesperson:** The team lead is the person who understands both the business context (what makes a good lead for their tenant) and the scoring system (what signals and weights mean). The admin has system-level access but not tenant-level business context. The salesperson has operational context but not configuration authority. The team lead is the correct human in the loop.

**Recommendation format sent to team lead:**

> "Signal version 2.1 appears in 7 wrong-bucket leads this week for Gamoft. Common pattern: `pricing_intent` fired in 6 of those leads, but none converted. The Scoring Agent rated these leads with ≥80% confidence. Possible issue: `pricing_intent` may be overweighted for your B2B profile.
>
> Choose an action: **Re-run ICP + Signal Agent** / **Adjust signal weight manually** / **Update prompt template** / **Investigate further** / **Dismiss**"

**Available actions and what each triggers:**

| Action | What happens | When to use |
|---|---|---|
| Re-run ICP + Signal Agent | Triggers Pipeline 2 — ICP Agent re-runs first, then Signal Agent uses updated ICP. New signal version created. Future leads use new version. | The ICP itself is wrong — the tenant's target customer type has changed |
| Adjust weight manually | Admin updates signal weights in `signal_definitions` or `tenant_config`. No Pipeline 2 re-run. | The signals are correct but their relative importance needs tuning |
| Update prompt template | Admin edits prompt in `prompt_registry`. New prompt version created. Future leads use new version. | The scoring instructions themselves are ambiguous or miscalibrated |
| Investigate further | Pattern flagged but no action. Team lead can pull individual lead cards to inspect. | The pattern looks suspicious but there is not yet enough evidence to act |
| Dismiss | Pattern logged as dismissed. Does not re-surface unless new evidence accumulates. | The pattern is a known anomaly or one-time event |

**Why five options, not one:** Forcing a single remediation path (e.g., always re-run ICP + Signal) would be excessive for problems that only require a weight tweak, and insufficient for problems that require a full ICP revision. The recommendation must match the severity and nature of the pattern. The team lead selects the appropriate response based on their business judgment.

**Rule `[LOCKED]`:** System suggests, human approves. Never automated.

**Why this rule is locked:** The system has no ground truth. It identifies patterns in negative feedback, but it cannot determine whether those patterns reflect genuine model failure or a temporary market shift that will self-correct. A human who understands the tenant's business context must make that call. Automating it risks making changes based on statistical noise, compounding errors rather than correcting them.

**Notification delivery:** `[TBD — in-chat message, email, or both]`

### 5.6 How Feedback Connects to Existing Quality Metrics

| Quality metric | How feedback feeds it |
|---|---|
| AP1 — Bucket Outcome Rate | `outcome` field in `feedback_events` is the positive/negative signal |
| AR5 — Salesperson Priority Alignment | Thumbs up/down vs bucket assignment tells us if salesperson agreed with bucket |
| C1 — Cross-Run Stability | If re-run after feedback produces different buckets, stability metric captures this |
| Score Coverage | Attribution job tracks what % of delivered leads received any feedback |

Full metric definitions: [[analyses/scoring-quality-metrics]]

### 5.7 Proactive Tenant Business Check-In

**Why this exists:** Personas and ICPs go stale. A tenant that was targeting SME clients 6 weeks ago may now be pushing enterprise. A B2C brand that focused on festival gifting in April has a completely different buyer profile in July. If the system never asks, it silently scores leads against an outdated profile — producing confidently wrong results that feedback loops will eventually catch, but only after weeks of degraded output.

The system proactively asks the tenant via the **existing chat interface** on a recurring schedule whether their business context has changed. This is the primary trigger for Pipeline 2 (ICP + Signal Agent) re-runs outside of feedback-driven patterns.

**Cadence:** `[TBD — tenant-configurable; suggest 2-week or monthly check-in as starting range]`

**Channel:** Same chat interface the salesperson uses — no new surface.

**Who receives it:** Team Lead of the tenant `[ASSUMPTION — confirm with team]`

**Check-in message format (business language, no technical terms):**

> "It's been [2 weeks / a month] — has anything changed in your business that might affect the kinds of leads you're looking for? For example: new markets, different customer types, new products, or a shift in what makes a lead valuable to you?"

Wording is per tenant language preference `[TBD — matches Confirmation UX language setting]`.

**Response handling — 4-step:**

```
1. Team lead responds in natural language in chat

2. Orchestrator calls Intent Classifier on the response:
     → "no changes" / "minor update" / "significant change"

3a. "No changes" → log check-in as completed, schedule next one
3b. "Minor update" → present specific field update options to team lead
    (e.g., "Which geography did you add?") → admin updates tenant_config directly
3c. "Significant change" → summarise what changed in plain language →
    ask: "Should I update your scoring profile based on this?"
    → Team lead approves → trigger Pipeline 2: ICP Agent + Signal Agent re-run

4. Log check-in event to access_log
   { action: 'tenant_checkin', metadata: { response_type, change_detected, action_taken } }
```

**What triggers a Pipeline 2 re-run vs a direct config update:**

| Change type | Action | Why |
|---|---|---|
| New target geography, industry, or customer type | Pipeline 2 re-run (ICP + Signal) | The ICP definition must change, which cascades into all signal definitions |
| New product line added to scoring focus | Pipeline 2 re-run (ICP + Signal) | New products may require entirely new signal dimensions |
| Shift in decision-maker profile (e.g., SME → Enterprise) | Pipeline 2 re-run (ICP + Signal) | The buying signals for Enterprise are structurally different from SME |
| Change in signal weight only (e.g., "intent matters more now") | Admin updates `signal_definitions.weight` directly — no re-run | The signals themselves are correct; only their relative importance changed |
| Operational change (new salesperson, quota) | No action — not relevant to scoring | Scoring is about lead quality, not sales team structure |

**Rule `[LOCKED principle]`:** System suggests re-run, team lead approves. Never automatic.

**Connection to source doc Add-on 8 `[DEFERRED]`:** Add-on 8 (Business-Language User Confirmation) covers the signal vocabulary version of this — asking tenants about new signal patterns detected from data. This check-in is simpler: it is proactive, schedule-driven, and about business context, not signal performance. Both use the same chat surface and the same "suggest, human approves" principle.

### 5.8 Weight Adjustment Process (Monthly Review)

**How it works:** Even without a flagged pattern, team lead reviews aggregated feedback monthly:

- Pull quality snapshots (monthly cadence) from `quality_snapshots`
- Review AP1 per bucket — is HOT converting at expected rate?
- If HOT Bucket Outcome Rate is low → weights may need adjustment
- Admin updates `signal_definitions.weight_within_dimension` per signal
- NOT automated. Human decision, human execution `[LOCKED — source ref Section 11.6]`

**Why this is not automated:** Weight adjustments are not just a math problem. A low HOT outcome rate could mean the weights are wrong, the ICP is stale, the salesperson follow-up speed is slow, or external market conditions changed. The system cannot distinguish these causes from outcome data alone. A human who understands the business context must make the diagnosis before changing weights.

---

## 6. Quality Tracking

### 6.1 Approach

**What it does:** Computes all scoring quality metrics on a schedule, stores results, and surfaces them for team lead review.

**How it works:** Scheduled SQL jobs run against existing Postgres tables. Results are written to `quality_snapshots` per metric per tenant per cadence.

**Why SQL jobs against existing tables, not a separate analytics system:** Every metric in [[analyses/scoring-quality-metrics]] is computable from data the system already writes — `pipeline_log`, `leads`, and `feedback_events`. Adding a separate analytics database would create a data synchronisation problem: two systems holding the same data, potentially diverging. Scheduled SQL jobs against Postgres stay in sync by definition — they read the same source of truth the orchestrator writes to. No new infrastructure means no new failure surface.

All quality metrics defined in [[analyses/scoring-quality-metrics]] are computable from:
- `pipeline_log` — lineage and stage data, signal values, confidence per lead
- `leads` — scores, buckets, pipeline_stage
- `feedback_events` — salesperson verdicts and outcome tags

Results written to a `quality_snapshots` table per metric per tenant per cadence.

```sql
CREATE TABLE quality_snapshots (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   TEXT        NOT NULL,
  metric_id   TEXT        NOT NULL,
  cadence     TEXT        NOT NULL,
  value       NUMERIC,
  metadata    JSONB,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6.2 Three Cadences

**Why three cadences, not one:** Each cadence answers a different question at a different time horizon. Collapsing them into a single daily or weekly job would either miss real-time operational failures (score coverage drops undetected for a week) or produce statistically meaningless outcome metrics (AP1 computed on 10 outcomes instead of 100+).

- **Per-run** answers: *Is the pipeline working right now?* Score coverage and failure rates are operational signals — they matter within minutes of a run completing, not a week later. Any drop here blocks trust in all other metrics.
- **Weekly** answers: *Are salespeople acting on the scores?* SLA compliance and action rates require a full week of behaviour data to be meaningful — a single day is too noisy, and Monday's data alone misrepresents the full working week.
- **Monthly** answers: *Is scoring creating business value?* Outcome rates (AP1, AP2) require enough closed leads to produce a statistically valid signal. 100 outcomes per bucket is the validity floor. A monthly cycle respects the typical sales cycle length — outcome data from Week 1 often does not resolve until Week 3 or 4.

**Per-run (immediate — end of every Pipeline 1 run):**

| Metric ID | Metric | What is computed |
|---|---|---|
| — | Score Coverage Rate | % of leads successfully scored out of total attempted |
| — | Confidence distribution | % of leads in each confidence band (≥80%, 50–79%, <50%) |
| — | Bucket distribution | HOT / WARM / COLD counts |
| — | Pipeline failure rate | % leads reaching `failed` state |
| — | Human review rate | % leads routed to `human_review` |

**Weekly (scheduled job, every Monday):**

| Metric ID | Metric | What is computed |
|---|---|---|
| AR1 | SLA Compliance Rate | % HOT leads contacted within 24h, WARM within 2-3d |
| AR2 | Action Rate by Bucket | % leads per bucket with recorded action taken |
| AR3 | Time-to-Action Distribution | Distribution of hours from delivery to first action |
| AR4 | Action Type by Bucket | Breakdown of action types (call, WhatsApp, email) per bucket |
| C1 | Cross-Run Bucket Stability | % leads that stay in same bucket across consecutive runs |
| C2 | Temporal Score Drift | Average score change per lead between runs |

**Monthly (scheduled job, needs outcome data to accumulate):**

| Metric ID | Metric | What is computed |
|---|---|---|
| AP1 | Bucket Outcome Rate | Positive outcome rate per bucket (HOT, WARM, COLD) |
| AP2 | Bucket Separation | BOR_HOT / BOR_COLD discrimination ratio |
| AP3 | Completeness Qualifier | % leads passing data completeness threshold |
| C4 | Decay-Rescore Coherence | Correlation between score decay and rescore direction |
| AR5 | Salesperson Priority Alignment | % salesperson-chosen leads matching HOT bucket |

### 6.3 Who Reviews

| Cadence | Who reviews | What action they can take |
|---|---|---|
| Per-run | Automated — alert fires if threshold breached | Engineering lead investigates pipeline logs |
| Weekly | Team lead reviews dashboard / report | Coaching salesperson on SLA compliance; flagging AR anomalies |
| Monthly | Team lead + product owner review | Weight adjustment consideration; threshold recalibration |

**Weight adjustment rule `[from playbook Section 12]`:** Review scoring weights monthly or quarterly based on actual wins, losses, and reorder data. Adjustments are NOT automated in v2.0 — human-reviewed and manually applied.

### 6.4 Alert Thresholds

All thresholds: `[TBD — team input after Month 1 baseline data collected]`

Suggested starting points are listed in Section 2.3 (Monitoring). Quality-specific alerts should be reviewed after Month 1 baseline data is collected, consistent with the principle: **measure first, set targets after Month 1**. Setting thresholds before baseline data exists produces arbitrary numbers that will need to be reset anyway — and that fire false alerts in the interim.

---

## 7. Security Controls

### 7.1 Architecture — Three Layers

```
Layer 1: Tenant Isolation    → Postgres RLS + application scoping
Layer 2: Authentication      → JWT with tenant_id claim
Layer 3: Access Control      → 4-role RBAC
```

Plus: credential management, PII handling, audit trail, data retention.

**Why three layers, not one:** Each layer defends against a different failure mode. No single mechanism covers all three.

- **Layer 1 (RLS)** defends against *code bugs* — a query that forgets a `WHERE tenant_id = ?` clause is blocked at the database level, not by application code. Application code can be buggy. Postgres RLS cannot be bypassed by a missing WHERE clause.
- **Layer 2 (JWT)** defends against *identity spoofing* — every request proves who made it and which tenant they belong to before any data is touched. Without this, anyone with a valid token could claim any tenant identity.
- **Layer 3 (RBAC)** defends against *privilege misuse* — even a valid, authenticated user of the correct tenant can only do what their role permits. A salesperson cannot trigger a Pipeline 2 re-run; only a team lead or admin can.

The three layers are multiplicative, not additive: RLS works correctly regardless of application code bugs. JWT authentication works regardless of which role the user claims. RBAC works regardless of which data the user can reach. Each layer assumes the others can fail.

### 7.2 Layer 1 — Tenant Isolation `[highest priority]`

**How it works:** Postgres Row-Level Security (RLS) is applied to every table with a `tenant_id` column. Every query is automatically filtered to the current tenant's rows — the application code cannot accidentally return another tenant's data, even if it forgets to add a filter.

```sql
CREATE POLICY tenant_isolation ON leads
  USING (tenant_id = current_setting('app.current_tenant_id'));
```

Applied to every table with a `tenant_id` column: `leads`, `pipeline_log`, `personas`, `signal_definitions`, `feedback_events`, `attributed_feedback`, `quality_snapshots`, `access_log`, `user_roles`.

Application layer also scopes every query with `WHERE tenant_id = ?` — two walls, not one. If code has a bug and omits the filter, Postgres blocks the cross-tenant read.

**Result:** Urvee's team lead never sees Gamoft's feedback patterns. Enforced at DB level, independent of application code.

### 7.3 Layer 2 — Authentication

**How it works:** Every API request carries a JWT token. The server validates the token signature, extracts the `tenant_id` and `role` claims, and sets the Postgres session variable that activates RLS before executing any query.

```json
{
  "user_id": "uuid",
  "tenant_id": "gamoft_001",
  "role": "team_lead",
  "iat": 1745000000,
  "exp": 1745003600
}
```

- Every API request validates JWT signature
- Extracts `tenant_id` → sets `app.current_tenant_id` in Postgres session → RLS activates
- Extracts `role` → enforces RBAC at endpoint level
- Token expiry: 1 hour. Refresh token: longer-lived, rotated on use
- Implementation: `[TBD — per chosen backend language]`

### 7.4 Layer 3 — RBAC (4 Roles)

**How it works:** Four roles, each with a distinct permission scope. The role is carried in the JWT, enforced at the API endpoint level, and logged to `access_log` for every action.

| Role | Who | Permissions |
|---|---|---|
| `admin` | Gamoft system admin | Full access: configure tenant settings, manage users, trigger Pipeline 2, manage prompt templates, view all data across tenants |
| `team_lead` | Tenant-side lead (per tenant) | Receive enforcement recommendations, approve/dismiss actions, review quality reports, manage salesperson assignments — scoped to own tenant only |
| `salesperson` | Tenant-side sales rep | View assigned leads, submit feedback (thumbs up/down, outcome tags), view own action metrics |
| `viewer` | Read-only stakeholder | Aggregated metrics only — no lead PII, no individual lead cards |

```sql
CREATE TABLE user_roles (
  user_id    UUID        NOT NULL,
  tenant_id  TEXT        NOT NULL,
  role       TEXT        NOT NULL CHECK (role IN ('admin', 'team_lead', 'salesperson', 'viewer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, tenant_id)
);
```

**Why four roles, not two or ten:** Four roles maps to the four distinct permission boundaries that exist in practice: system-level (admin), tenant-level management (team_lead), tenant-level execution (salesperson), and read-only (viewer). Fewer roles means either over-permissioning (salesperson can approve re-runs) or under-permissioning (team_lead cannot review reports). More roles creates management complexity without adding meaningful access boundaries.

**Team lead is tenant-scoped.** Each tenant has their own team lead who sees only their tenant's recommendations, quality reports, and feedback patterns — not other tenants'. RLS enforces this automatically.

**Salesperson lead scoping:** A salesperson sees only leads assigned to them.

```sql
-- Additional filter for salesperson role (applied on top of RLS)
WHERE assigned_to = current_user_id   -- if role = 'salesperson'
-- No additional filter for team_lead or admin
```

### 7.5 Credential Management

**How it works:** Channel API credentials are stored in a secrets vault, never in the database or application code. The database stores only a path reference. The orchestrator resolves the path to a credential at runtime, immediately before the tool call that needs it.

**Why not store credentials in the database:** A database credential leak exposes all credentials for all tenants simultaneously. A secrets vault leak exposes one credential per compromised path. Vault access is also audited per fetch — the DB is not. Credentials are rotated per channel per tenant independently, without touching any application code.

| Rule | Detail |
|---|---|
| Storage | Secrets vault — AWS Secrets Manager (if AWS) or HashiCorp Vault `[TBD]` |
| Scoping | One credential set per channel per tenant — isolated per tenant |
| Rotation | Per tenant, per channel, independently |
| Access logging | Every credential fetch logged: `(tenant_id, credential_name, accessed_by, timestamp)` |
| Reference in DB | DB stores `vault_path` reference only, never the credential value |

### 7.6 PII Handling

**Why PII is encrypted at rest but scores are not:** Phone numbers, emails, and names identify a real person. If the database is breached, unencrypted PII is immediately usable for harm. Scores, buckets, and signal values are meaningless without the identity data — a score of 84 is not PII. Encrypting all fields would add decryption overhead to every query; encrypting only PII fields limits the overhead to identity lookups while protecting what actually needs protection.

| Field | Handling |
|---|---|
| Phone number | Encrypted at rest in `leads` table |
| Email | Encrypted at rest |
| Name | Encrypted at rest |
| Address / location | Encrypted at rest |
| Score, bucket, signals | Not encrypted (not PII) |
| Decryption | Application layer only |

Encryption implementation: `[TBD — per chosen backend language/library]`

### 7.7 Data Retention

**Why retention matters:** Indefinite retention of PII creates legal risk under GDPR, DPDP, and similar regulations. Scheduled archival keeps the active dataset clean and limits the blast radius of a breach to recent data rather than years of history.

Retention policy: `[TBD — per jurisdiction and legal requirements]`

Suggested starting points:
- `leads`: 2 years from last update
- `pipeline_log`: 2 years
- `attributed_feedback`: 2 years
- `access_log`: 5 years
- `quality_snapshots`: 1 year

**Archival job** runs on schedule — moves expired records to cold storage or deletes per policy. Hard deletes only during archival — never during normal operation.

**Soft delete on all tables:**

```sql
deleted_at TIMESTAMPTZ NULL   -- null = active, non-null = soft-deleted
```

Queries always filter `WHERE deleted_at IS NULL`.

---

## 8. New Tables Added by Governance Layer

| Table | Purpose | Defined in |
|---|---|---|
| `access_log` | User action audit trail | Section 3.2 |
| `quality_snapshots` | Quality metric results per cadence | Section 6.1 |
| `user_roles` | RBAC role assignments (4 roles) | Section 7.4 |
| `attributed_feedback` | Feedback enriched with lineage data | Section 5.3 |

These are in addition to tables already defined by S1 (`leads`, `pipeline_log`, `tenant_config`, `personas`, `signal_definitions`, `feedback_events`, `prompt_registry`).

---

## 9. Open Questions

| Item | Status |
|---|---|
| Monitoring alert thresholds | `[TBD — team input after Month 1 baseline]` |
| Alert delivery mechanism (chat/email/both) | `[TBD — team decision]` |
| Observability tooling (Grafana/Datadog/custom) | `[TBD]` |
| Retention policy per jurisdiction | `[TBD — legal/compliance input]` |
| Secrets vault choice (AWS Secrets Manager vs HashiCorp) | `[TBD — infra decision]` |
| PII encryption library per backend | `[TBD — depends on backend language choice]` |
| Auth library choice | `[TBD — depends on backend language choice]` |
| `leads.assigned_to` field existence + type | `[TBD from S1]` |
| Quality snapshot retention | `[TBD — suggest 1 year]` |
| Tenant check-in cadence | `[TBD — suggest 2-week or monthly; team decision]` |
| Check-in recipient | `[TBD — team_lead assumed; confirm with team]` |
| Check-in message wording | `[TBD — per tenant language preference; matches Confirmation UX language setting]` |
| Flagging threshold for pattern detection (value of N) | `[TBD — team decision after Month 1 data]` |

---

## 10. Confirmed Decisions

| Decision | Basis |
|---|---|
| Governance layer cross-cuts both pipelines, not in critical path | Team decision 2026-04-19 |
| Failure in governance layer must not halt pipelines | Team decision 2026-04-19 |
| Two audit surfaces: pipeline_log (transformations) + access_log (user actions) | Team decision 2026-04-19 |
| Lineage written by orchestrator only — not by individual tools | Team decision 2026-04-19 |
| Lineage must be built before adding the second LLM agent | Team decision 2026-04-19 |
| Feedback loop is 3 steps: collection → attribution → pattern detection → recommendation | Team decision 2026-04-19 |
| Attribution fires immediately on every feedback event — not batched | Team decision 2026-04-19 |
| Pattern detection is weekly — fixed count threshold, not rate-based | Team decision 2026-04-19 |
| System suggests feedback-driven actions — team lead always approves | `[LOCKED principle]` |
| Proactive tenant check-in via chat on recurring schedule | Team decision 2026-04-19 |
| Check-in triggers ICP + Signal Agent re-run on significant change (human-approved) | Team decision 2026-04-19 |
| Check-in logged to access_log | Team decision 2026-04-19 |
| Three quality cadences: per-run, weekly, monthly | Team decision 2026-04-19 |
| Quality computed via scheduled SQL jobs — no new infrastructure | Team decision 2026-04-19 |
| Quality snapshots stored in `quality_snapshots` table | Team decision 2026-04-19 |
| Weight adjustments human-reviewed monthly, not automated | Source ref + playbook |
| Three-layer security: RLS + JWT + RBAC | Team decision 2026-04-19 |
| Postgres RLS on every tenant-scoped table | Team decision 2026-04-19 |
| JWT with tenant_id + role claims | Team decision 2026-04-19 |
| 4 roles: admin, team_lead, salesperson, viewer | Team decision 2026-04-19 |
| team_lead is tenant-scoped — each tenant has own team lead | Team decision 2026-04-19 |
| Credentials in secrets vault — never in DB or code | `[LOCKED]` source ref |
| PII encrypted at rest | Team decision 2026-04-19 |
| Soft deletes only during normal operation | Team decision 2026-04-19 |
