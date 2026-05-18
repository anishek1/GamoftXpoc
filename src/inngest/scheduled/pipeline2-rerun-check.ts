/**
 * Pipeline 2 Re-Run Check — Bi-Weekly Scheduled Job
 *
 * Implements the "system proposes, team lead approves" principle for Pipeline 2 re-runs.
 * Two triggers can prompt a re-run proposal:
 *   1. Proactive check-in: sends a message to the team lead asking if anything
 *      has changed in their business (cadence: every 2 weeks, per tenant).
 *   2. Feedback-driven: the governance layer detected that a signal version or
 *      prompt version keeps producing wrong-bucket leads → recommendation surfaced here.
 *
 * Rule: the system proposes; the team lead ALWAYS approves. Never automatic.
 * When a team lead approves, they trigger "tenant/onboarding.start" with
 * trigger: "team_lead_approved_rerun".
 */

import { inngest } from "../client";
import { db, notifyTeamLead } from "../../lib/db";

export const pipeline2RerunCheck = inngest.createFunction(
  {
    id: "pipeline2-rerun-check",
    name: "Pipeline 2 Re-Run Check — Bi-Weekly",
    concurrency: { limit: 1 },
  },
  { cron: "0 9 1,15 * *" }, // 1st and 15th of each month at 09:00 UTC
  async ({ step }) => {
    const tenants = await step.run("load_active_tenants", async () => {
      return db.tenants.findAll({ status: "active" });
    });

    for (const tenant of tenants) {
      await step.run(`rerun_check_tenant_${tenant.tenant_id}`, async () => {
        // ── Check 1: Proactive check-in ─────────────────────────────────────
        // Ask the team lead if anything has changed since last Pipeline 2 run.
        const lastRun = await db.pipeline_runs.findLatest({
          tenant_id: tenant.tenant_id,
          pipeline: "onboarding",
          status: "complete",
        });

        const daysSinceLastRun = lastRun
          ? Math.floor(
              (Date.now() - new Date(lastRun.ended_at).getTime()) /
                (1000 * 60 * 60 * 24)
            )
          : Infinity;

        if (daysSinceLastRun >= 14) {
          await notifyTeamLead({
            tenant_id: tenant.tenant_id,
            alert_type: "pipeline2_checkin",
            summary: {
              message:
                `It's been ${daysSinceLastRun} days since your scoring intelligence was last updated. ` +
                `Have you entered new markets, launched new products, or changed your target customer profile? ` +
                `If yes, we recommend refreshing your scoring setup.`,
              action_label: "Refresh scoring setup",
              action_event: "tenant/onboarding.start",
              action_data: {
                tenant_id: tenant.tenant_id,
                trigger: "team_lead_approved_rerun",
                rerun_reason: "proactive_checkin",
              },
              last_pipeline2_run: lastRun?.ended_at ?? "never",
            },
            channel: tenant.tenant_config.alert_channel ?? "chat",
          });
        }

        // ── Check 2: Feedback-driven signals ────────────────────────────────
        // If the governance layer has flagged systematic wrong-bucket patterns
        // for this tenant's current signal/prompt version, surface a recommendation.
        const feedbackSignals = await db.quality_snapshots.findAll({
          tenant_id: tenant.tenant_id,
          metric_name_in: ["ap1_bucket_outcome_rate_hot", "ap2_discrimination_ratio"],
          cadence: "monthly",
          computed_after: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        });

        const ap2 = feedbackSignals.find(
          (s: { metric_name: string }) => s.metric_name === "ap2_discrimination_ratio"
        );

        // AP2 Discrimination Ratio near 1.0 means buckets are not separating well.
        // This suggests signal definitions need refreshing.
        if (ap2 && (ap2 as { value: number }).value < 1.2) {
          await notifyTeamLead({
            tenant_id: tenant.tenant_id,
            alert_type: "pipeline2_feedback_rerun",
            summary: {
              message:
                `Your lead scoring is producing similar conversion rates across HOT, WARM, and COLD buckets ` +
                `(discrimination ratio: ${(ap2 as { value: number }).value.toFixed(2)}). ` +
                `This suggests your signal definitions may need updating. ` +
                `Would you like to refresh your scoring intelligence?`,
              action_label: "Refresh scoring setup",
              action_event: "tenant/onboarding.start",
              action_data: {
                tenant_id: tenant.tenant_id,
                trigger: "team_lead_approved_rerun",
                rerun_reason: "feedback_driven_low_discrimination",
              },
              metric: { name: "ap2_discrimination_ratio", value: (ap2 as { value: number }).value },
            },
            channel: tenant.tenant_config.alert_channel ?? "chat",
          });
        }
      });
    }
  }
);
