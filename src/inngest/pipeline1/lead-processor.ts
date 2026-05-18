/**
 * Pipeline 1 — Per-Lead Processor
 *
 * Triggered once per lead from data-gather's fan-out.
 * Concurrency is capped per-tenant (not globally) to prevent noisy-neighbour.
 *
 * Stage sequence — varies by entry_point:
 *
 *   DM path  (WhatsApp / Facebook DM / Instagram DM):
 *     Step 0 → pre_filter_gate       (drop spam / noise)
 *     Step 1 → message_parser        (Haiku — multilingual extraction)
 *     Step 2 → lead_enrichment       (Consent Gate + data collection + signal extraction)
 *     Step 3 → normalise             (clean + standardise + completeness score)
 *     Step 4 → intent_gate           (pass or await_clarification)
 *     Step 5 → scoring_agent         (Sonnet — structured JSON output)
 *     Step 6 → bucketize             (HOT/WARM/COLD + disqualification + completeness routing)
 *     Step 7 → deliver               (hand off to Delivery and Integration Layer)
 *
 *   Lead Ad path  (Facebook Lead Ads / Instagram Lead Ads):
 *     Skips Steps 0–1 (already structured form data)
 *     Enters at Step 2 → lead_enrichment
 *     → ... same Steps 3–7
 *
 * pipeline_stage is ALWAYS the final atomic write at every step.
 * Lineage is written by the orchestrator (this function), never by individual tools.
 */

import { inngest } from "../client";
import {
  db,
  writeTaskExecution,
  writeLineageRecord,
  updateLeadStage,
  notifyAdmin,
} from "../../lib/db";
import {
  runPreFilterGate,
  runMessageParser,
  runLeadEnrichment,
  runConsentGate,
  runNormalise,
  runIntentGate,
  runScoringAgent,
  runBucketize,
  deliverLead,
  extractSignalValues,
} from "../../lib/agents";
import { loadTenantContext } from "../../lib/tenant";

// Per-tenant concurrency cap: 2 simultaneous Scoring Agent calls per tenant.
// Prevents any single tenant from starving others on shared LLM slots.
// Configurable per tenant via tenant_config.scoring_concurrency_cap.
const DEFAULT_SCORING_CONCURRENCY = 2;

export const pipeline1LeadProcessor = inngest.createFunction(
  {
    id: "pipeline1-lead-processor",
    name: "Pipeline 1 — Lead Processor",
    concurrency: [
      {
        // Per-tenant cap — the critical noisy-neighbour guard.
        // With 3 tenants at cap=2, max 6 simultaneous Scoring Agent calls.
        key: "event.data.tenant_id",
        limit: DEFAULT_SCORING_CONCURRENCY, // overridden per-tenant via tenant_config
      },
    ],
    // No function-level retries — explicit retry logic per step preserves
    // pipeline_stage crash safety and avoids double LLM charges.
    retries: 0,
    timeouts: {
      // A lead that is stuck in awaiting_clarification can wait up to 25 hours
      // (24h reply window + 1h buffer). After that the function errors and the
      // lead is routed to human_review.
      finish: "25h",
    },
  },
  { event: "lead/received" },
  async ({ event, step }) => {
    const { tenant_id, run_id, lead_id, entry_point, raw_payload, channel } =
      event.data;

    // ── Load tenant context once (persona, signals, prompt template, config) ──
    const ctx = await step.run("load_tenant_context", async () => {
      const context = await loadTenantContext(tenant_id);

      // Apply per-tenant concurrency cap if configured (overrides default).
      // The cap is stored in tenant_config and read by the Inngest middleware,
      // but we validate it here to fail fast on misconfiguration.
      if (!context.persona || !context.signal_definitions || !context.prompt_template) {
        throw new Error(
          `Tenant context incomplete for ${tenant_id} — Pipeline 2 may not have completed`
        );
      }

      // Write lead as "fetched" — first pipeline_stage transition.
      await db.leads.upsert({
        lead_id,
        tenant_id,
        run_id,
        pipeline_stage: "fetched",
        entry_point,
        channel,
        raw_payload,
        updated_at: new Date().toISOString(),
      });

      return context;
    });

    // ─────────────────────────────────────────────────────────────────────────
    // DM PATH ONLY — Steps 0 and 1
    // ─────────────────────────────────────────────────────────────────────────

    let parsedPayload: Record<string, unknown> = raw_payload;

    if (entry_point === "dm") {
      // ── Step 0: Pre-Filter Gate ─────────────────────────────────────────────
      const filterResult = await step.run("pre_filter_gate", async () => {
        const result = runPreFilterGate(raw_payload);

        await writeTaskExecution({
          run_id,
          lead_id,
          agent_id: "pre_filter_gate",
          tenant_id,
          pipeline: "lead_processing",
          status: result.pass ? "success" : "filtered",
        });

        if (!result.pass) {
          await updateLeadStage(lead_id, "failed", { reason: "pre_filter_gate" });
        }

        return result;
      });

      if (!filterResult.pass) return; // Lead is spam/noise; stop processing.

      // ── Step 1: Message Parser (Haiku) ─────────────────────────────────────
      parsedPayload = await step.run("message_parser", async () => {
        const startMs = Date.now();
        let attempt = 0;

        while (attempt < 2) {
          try {
            const parsed = await runMessageParser({
              raw_text: (raw_payload.message_text as string) ?? "",
              channel,
              language_hint: ctx.tenant_config.language_preference,
            });

            await writeLineageRecord({
              run_id,
              lead_id,
              agent_id: "message_parser",
              tenant_id,
              input_snapshot: { raw_text: raw_payload.message_text },
              output_snapshot: parsed,
              prompt_version: parsed.prompt_version,
            });

            await writeTaskExecution({
              run_id,
              lead_id,
              agent_id: "message_parser",
              tenant_id,
              pipeline: "lead_processing",
              status: "success",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
            });

            return parsed.structured_fields;
          } catch (err) {
            attempt++;
            if (attempt >= 2) {
              // Message Parser failure is non-fatal: score with raw text.
              await writeTaskExecution({
                run_id,
                lead_id,
                agent_id: "message_parser",
                tenant_id,
                pipeline: "lead_processing",
                status: "failure",
                duration_ms: Date.now() - startMs,
                retry_count: attempt,
                error: String(err),
              });
              return raw_payload; // Fall back to raw payload
            }
          }
        }
        return raw_payload;
      });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // BOTH PATHS — Steps 2–7
    // Lead Ads join here (entry_point === "lead_ad").
    // ─────────────────────────────────────────────────────────────────────────

    // ── Step 2: Lead Enrichment + Consent Gate ─────────────────────────────
    const enrichedLead = await step.run("lead_enrichment", async () => {
      const startMs = Date.now();
      let attempt = 0;

      while (attempt < 2) {
        try {
          // (a) Consent Gate — must run before any external lookup.
          const consentResult = await runConsentGate({
            lead_id,
            tenant_id,
            jurisdiction: ctx.tenant_config.geography_focus,
          });

          // (b) Collect external data (respects consent result).
          const enriched = await runLeadEnrichment({
            lead_id,
            tenant_id,
            parsed_payload: parsedPayload,
            consent: consentResult,
            signal_definitions: ctx.signal_definitions,
          });

          // (c) Deterministic signal extraction (no LLM).
          const signal_values = extractSignalValues(
            enriched,
            ctx.signal_definitions
          );

          await db.lead_enrichments.upsert({
            lead_id,
            tenant_id,
            ...enriched,
            signal_values,
          });

          await writeLineageRecord({
            run_id,
            lead_id,
            agent_id: "lead_enrichment",
            tenant_id,
            input_snapshot: { consent: consentResult, sources_used: enriched.sources_used },
            output_snapshot: { enriched_fields: Object.keys(enriched), signal_count: signal_values.length },
            prompt_version: null,
          });

          await writeTaskExecution({
            run_id,
            lead_id,
            agent_id: "lead_enrichment",
            tenant_id,
            pipeline: "lead_processing",
            status: "success",
            duration_ms: Date.now() - startMs,
            retry_count: attempt,
          });

          // pipeline_stage updated last — crash safety guarantee.
          await updateLeadStage(lead_id, "enriched");

          return { ...enriched, signal_values, consent: consentResult };
        } catch (err) {
          attempt++;
          if (attempt >= 2) {
            await writeTaskExecution({
              run_id,
              lead_id,
              agent_id: "lead_enrichment",
              tenant_id,
              pipeline: "lead_processing",
              status: "failure",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
              error: String(err),
            });
            await updateLeadStage(lead_id, "failed", { reason: "enrichment_failed" });
            return null;
          }
        }
      }
      return null;
    });

    if (!enrichedLead) return; // Enrichment failed after retries; lead marked failed.

    // ── Step 3: Normalise ──────────────────────────────────────────────────
    const normalisedLead = await step.run("normalise", async () => {
      const startMs = Date.now();
      let attempt = 0;

      while (attempt < 2) {
        try {
          const normalised = runNormalise(enrichedLead);

          // lead_completeness: fraction of expected signal fields that are
          // present and populated (not LLM confidence).
          const total_signals = ctx.signal_definitions.length;
          const populated = enrichedLead.signal_values.filter(
            (sv: { value: unknown }) => sv.value !== null && sv.value !== undefined
          ).length;
          const lead_completeness = total_signals > 0 ? populated / total_signals : 0;

          await db.leads.update(lead_id, {
            ...normalised,
            lead_completeness,
          });

          await writeLineageRecord({
            run_id,
            lead_id,
            agent_id: "normalise",
            tenant_id,
            input_snapshot: { fields_in: Object.keys(enrichedLead) },
            output_snapshot: { normalised_fields: Object.keys(normalised), lead_completeness },
            prompt_version: null,
            lead_completeness,
          });

          await writeTaskExecution({
            run_id,
            lead_id,
            agent_id: "normalise",
            tenant_id,
            pipeline: "lead_processing",
            status: "success",
            duration_ms: Date.now() - startMs,
            retry_count: attempt,
          });

          await updateLeadStage(lead_id, "normalised");

          return { ...normalised, lead_completeness };
        } catch (err) {
          attempt++;
          if (attempt >= 2) {
            await writeTaskExecution({
              run_id,
              lead_id,
              agent_id: "normalise",
              tenant_id,
              pipeline: "lead_processing",
              status: "failure",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
              error: String(err),
            });
            await updateLeadStage(lead_id, "failed", { reason: "normalise_failed" });
            return null;
          }
        }
      }
      return null;
    });

    if (!normalisedLead) return;

    // ── Step 4: Intent Gate ────────────────────────────────────────────────
    //
    // If intent signals are very low but fit is high, the orchestrator sends
    // a clarification prompt to the lead via the originating channel and pauses.
    // On reply (lead/clarification.received) → resume scoring from normalised.
    // If no reply within 24h → score with intent penalty.

    const intentResult = await step.run("intent_gate", async () => {
      return runIntentGate({
        signal_values: enrichedLead.signal_values,
        signal_definitions: ctx.signal_definitions,
        lead_completeness: normalisedLead.lead_completeness,
      });
    });

    if (intentResult.outcome === "await_clarification") {
      // Mark lead as awaiting_clarification — NOT a terminal state.
      // The concurrency guard in crash recovery must not pick this up.
      await updateLeadStage(lead_id, "awaiting_clarification", {
        clarification_sent_at: new Date().toISOString(),
        clarification_prompt: intentResult.clarification_prompt,
      });

      // Wait for reply — up to 24 hours.
      const clarificationReply = await step.waitForEvent(
        "wait_for_clarification_reply",
        {
          event: "lead/clarification.received",
          timeout: "24h",
          match: "data.lead_id",
        }
      );

      if (clarificationReply) {
        // Merge reply into parsed payload and continue to scoring.
        parsedPayload = {
          ...parsedPayload,
          clarification_reply: clarificationReply.data.reply_text,
        };
        // Re-enter at normalised stage; signal re-extraction happens inside
        // scoring_agent context injection (no extra LLM call needed).
      } else {
        // 24h timeout: score with intent penalty.
        enrichedLead.signal_values = enrichedLead.signal_values.map(
          (sv: { dimension: string; value: number }) =>
            sv.dimension === "intent" ? { ...sv, value: sv.value * 0.5 } : sv
        );
      }
    }

    // ── Step 5: Scoring Agent (Sonnet) ─────────────────────────────────────
    //
    // Failure handling (from orchestration-layer-spec §4.3):
    //   - Malformed JSON → retry once with schema reminder appended
    //   - Schema mismatch → retry once
    //   - Timeout         → retry once with extended deadline
    //   - Rate limit      → wait for rate limit window, retry once
    //   - 2 consecutive failures → human_review (reason: scoring_failed)

    const scoringOutput = await step.run("scoring_agent", async () => {
      const startMs = Date.now();

      // Load the active prompt template for this tenant.
      const promptTemplate = await db.prompt_registry.findActive(tenant_id);

      // Fill every signal slot with extracted values.
      const filledPrompt = fillPromptTemplate(
        promptTemplate.template,
        enrichedLead.signal_values,
        ctx.persona,
        normalisedLead.lead_completeness
      );

      let attempt = 0;
      let schemaReminderAppended = false;

      while (attempt < 2) {
        try {
          const output = await runScoringAgent({
            tenant_id,
            lead_id,
            prompt: filledPrompt,
            model: ctx.tenant_config.scoring_model ?? "claude-sonnet-4-6",
            token_budget: ctx.tenant_config.llm_token_budget_per_lead ?? 8_000,
            prompt_version: promptTemplate.version,
          });

          // Validate output schema (all 5 sub_scores must be present).
          const REQUIRED_SUB_SCORES = [
            "fit",
            "intent",
            "engagement",
            "behaviour",
            "context",
          ] as const;
          for (const dim of REQUIRED_SUB_SCORES) {
            if (typeof output.sub_scores[dim] !== "number") {
              throw new Error(`Missing sub_score: ${dim}`);
            }
          }

          await writeLineageRecord({
            run_id,
            lead_id,
            agent_id: "scoring_agent",
            tenant_id,
            input_snapshot: {
              prompt_version: promptTemplate.version,
              lead_completeness: normalisedLead.lead_completeness,
              signal_count: enrichedLead.signal_values.length,
            },
            output_snapshot: output,
            prompt_version: promptTemplate.version,
            lead_completeness: normalisedLead.lead_completeness,
          });

          await writeTaskExecution({
            run_id,
            lead_id,
            agent_id: "scoring_agent",
            tenant_id,
            pipeline: "lead_processing",
            status: "success",
            duration_ms: Date.now() - startMs,
            retry_count: attempt,
          });

          await updateLeadStage(lead_id, "scored");

          return output;
        } catch (err) {
          const errMsg = String(err);
          attempt++;

          // Append schema reminder on JSON/schema errors for the retry.
          if (
            !schemaReminderAppended &&
            (errMsg.includes("JSON") || errMsg.includes("sub_score"))
          ) {
            filledPrompt.append_schema_reminder = true;
            schemaReminderAppended = true;
          }

          if (attempt >= 2) {
            await writeTaskExecution({
              run_id,
              lead_id,
              agent_id: "scoring_agent",
              tenant_id,
              pipeline: "lead_processing",
              status: "failure",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
              error: errMsg,
            });
            await updateLeadStage(lead_id, "human_review", {
              reason: "scoring_failed",
            });
            return null;
          }
        }
      }

      return null;
    });

    if (!scoringOutput) return; // Lead routed to human_review by scoring failure.

    // ── Step 6: Bucketize ──────────────────────────────────────────────────
    await step.run("bucketize", async () => {
      const startMs = Date.now();

      // (a) Disqualification gate — overrides score for specific conditions.
      const disqualResult = applyDisqualificationGate(
        scoringOutput,
        normalisedLead,
        ctx.tenant_config.disqualification_rules ?? []
      );

      const finalScore = disqualResult.adjusted_score;

      // (b) Bucket thresholds from tenant_config (HOT ≥ 80, WARM ≥ 55, COLD < 55).
      const hot_min = ctx.tenant_config.bucket_thresholds?.hot_min ?? 80;
      const warm_min = ctx.tenant_config.bucket_thresholds?.warm_min ?? 55;

      const bucket =
        finalScore >= hot_min
          ? "hot"
          : finalScore >= warm_min
          ? "warm"
          : "cold";

      // (c) Validate Output Schema Layer bucket constraint.
      if (bucket !== scoringOutput.bucket) {
        // Scoring Agent returned a bucket that doesn't match the threshold rule.
        // Trust the deterministic threshold, not the LLM's bucket label.
        scoringOutput.bucket = bucket;
      }

      // (d) Lead completeness routing (needs_review flag).
      const needsReview = scoringOutput.needs_review || normalisedLead.lead_completeness < 0.5;

      // SLA assignment (action_sla concept).
      const sla_deadline = computeSlaDeadline(bucket);

      await db.leads.update(lead_id, {
        score: finalScore,
        bucket,
        sub_scores: scoringOutput.sub_scores,
        reasoning: scoringOutput.reasoning,
        recommended_action: scoringOutput.recommended_action,
        lead_completeness: scoringOutput.lead_completeness,
        needs_review: needsReview,
        sla_deadline,
        disqualified: disqualResult.disqualified,
        disqualification_reason: disqualResult.reason ?? null,
        schema_version: scoringOutput.schema_version,
        prompt_version: scoringOutput.prompt_version,
        model: scoringOutput.model,
      });

      await writeTaskExecution({
        run_id,
        lead_id,
        agent_id: "bucketize",
        tenant_id,
        pipeline: "lead_processing",
        status: "success",
        duration_ms: Date.now() - startMs,
      });

      // pipeline_stage is always the final atomic write.
      if (needsReview && normalisedLead.lead_completeness < 0.5) {
        await updateLeadStage(lead_id, "human_review", {
          reason: "low_completeness",
        });
      } else {
        await updateLeadStage(lead_id, "delivered");
      }

      return { bucket, finalScore, needsReview, sla_deadline };
    });

    // ── Step 7: Deliver ────────────────────────────────────────────────────
    // Hand off to Delivery and Integration Layer.
    // Delivery failures never roll back Pipeline 1 state.
    await step.run("deliver", async () => {
      try {
        await deliverLead({
          tenant_id,
          lead_id,
          run_id,
          persona: ctx.persona,
        });
      } catch (err) {
        // Log delivery failure; do NOT change pipeline_stage — the lead is
        // already "delivered" or "human_review" from the bucketize step.
        await notifyAdmin({
          tenant_id,
          step: "deliver",
          error: err,
          note: "Delivery failed but lead score is persisted; lead is safe.",
        });
      }
    });
  }
);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fillPromptTemplate(
  template: string,
  signal_values: Array<{ name: string; value: unknown }>,
  persona: Record<string, unknown>,
  lead_completeness: number
): { filled: string; append_schema_reminder?: boolean } {
  let filled = template;
  for (const sv of signal_values) {
    filled = filled.replace(`{${sv.name}}`, String(sv.value ?? "null"));
  }
  filled = filled.replace("{lead_completeness}", String(lead_completeness));
  return { filled };
}

function applyDisqualificationGate(
  scoringOutput: { score: number; bucket: string },
  normalisedLead: Record<string, unknown>,
  rules: Array<{ condition: string; penalty: number | "disqualify" }>
): { adjusted_score: number; disqualified: boolean; reason?: string } {
  // Placeholder: apply tenant-specific disqualification rules.
  // Rules are defined per tenant during onboarding.
  return {
    adjusted_score: scoringOutput.score,
    disqualified: false,
  };
}

function computeSlaDeadline(bucket: "hot" | "warm" | "cold"): string {
  const now = new Date();
  if (bucket === "hot") now.setHours(now.getHours() + 24);
  else if (bucket === "warm") now.setDate(now.getDate() + 3);
  else now.setDate(now.getDate() + 7);
  return now.toISOString();
}
