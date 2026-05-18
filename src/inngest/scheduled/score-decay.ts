/**
 * Score Decay — Scheduled Background Job
 *
 * Implements the score-decay concept from the architecture:
 *   -10 points at 7 days without activity
 *   -20 points at 14 days without activity
 *   auto-cold (score forced to COLD range) at 30 days
 *
 * Runs daily at 02:00 UTC across all active tenants.
 * Operates only on leads in "delivered" state with HOT or WARM buckets.
 * Governance failures (lineage writes) must not halt the decay run.
 */

import { inngest } from "../client";
import { db, writeLineageRecord, writeTaskExecution } from "../../lib/db";

export const scoreDecay = inngest.createFunction(
  {
    id: "score-decay",
    name: "Score Decay — Daily",
    concurrency: { limit: 1 }, // One decay run at a time globally.
  },
  { cron: "0 2 * * *" }, // Daily at 02:00 UTC
  async ({ step }) => {
    const now = new Date();

    // Process each active tenant in isolation.
    const tenants = await step.run("load_active_tenants", async () => {
      return db.tenants.findAll({ status: "active" });
    });

    for (const tenant of tenants) {
      await step.run(`decay_tenant_${tenant.tenant_id}`, async () => {
        const run_id = `decay-${tenant.tenant_id}-${now.toISOString().split("T")[0]}`;

        // ── 7-day decay: -10 points ──────────────────────────────────────────
        const sevenDaysAgo = new Date(now);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        const stale7d = await db.leads.findAll({
          tenant_id: tenant.tenant_id,
          pipeline_stage: "delivered",
          bucket_in: ["hot", "warm"],
          last_activity_before: sevenDaysAgo.toISOString(),
          last_activity_after: new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000).toISOString(),
          decay_level_not: "7d",
        });

        for (const lead of stale7d) {
          const newScore = Math.max(0, lead.score - 10);
          const newBucket = recomputeBucket(
            newScore,
            tenant.tenant_config.bucket_thresholds
          );

          await db.leads.update(lead.lead_id, {
            score: newScore,
            bucket: newBucket,
            decay_level: "7d",
            score_decayed_at: now.toISOString(),
          });

          try {
            await writeLineageRecord({
              run_id,
              lead_id: lead.lead_id,
              agent_id: "score_decay_7d",
              tenant_id: tenant.tenant_id,
              input_snapshot: { score_before: lead.score, bucket_before: lead.bucket },
              output_snapshot: { score_after: newScore, bucket_after: newBucket, decay: -10 },
              prompt_version: null,
            });
          } catch {
            // Lineage write failures do not stop the decay run.
          }
        }

        // ── 14-day decay: -20 points ─────────────────────────────────────────
        const fourteenDaysAgo = new Date(now);
        fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

        const stale14d = await db.leads.findAll({
          tenant_id: tenant.tenant_id,
          pipeline_stage: "delivered",
          bucket_in: ["hot", "warm"],
          last_activity_before: fourteenDaysAgo.toISOString(),
          last_activity_after: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          decay_level_not: "14d",
        });

        for (const lead of stale14d) {
          const newScore = Math.max(0, lead.score - 20);
          const newBucket = recomputeBucket(
            newScore,
            tenant.tenant_config.bucket_thresholds
          );

          await db.leads.update(lead.lead_id, {
            score: newScore,
            bucket: newBucket,
            decay_level: "14d",
            score_decayed_at: now.toISOString(),
          });

          try {
            await writeLineageRecord({
              run_id,
              lead_id: lead.lead_id,
              agent_id: "score_decay_14d",
              tenant_id: tenant.tenant_id,
              input_snapshot: { score_before: lead.score, bucket_before: lead.bucket },
              output_snapshot: { score_after: newScore, bucket_after: newBucket, decay: -20 },
              prompt_version: null,
            });
          } catch {
            // Non-fatal.
          }
        }

        // ── 30-day decay: auto-cold ──────────────────────────────────────────
        const thirtyDaysAgo = new Date(now);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        const stale30d = await db.leads.findAll({
          tenant_id: tenant.tenant_id,
          pipeline_stage: "delivered",
          bucket_in: ["hot", "warm"],
          last_activity_before: thirtyDaysAgo.toISOString(),
          decay_level_not: "30d",
        });

        for (const lead of stale30d) {
          // Force to COLD regardless of current score.
          const coldScore = Math.min(
            lead.score,
            (tenant.tenant_config.bucket_thresholds?.warm_min ?? 55) - 1
          );

          await db.leads.update(lead.lead_id, {
            score: coldScore,
            bucket: "cold",
            decay_level: "30d",
            score_decayed_at: now.toISOString(),
          });

          try {
            await writeLineageRecord({
              run_id,
              lead_id: lead.lead_id,
              agent_id: "score_decay_30d_auto_cold",
              tenant_id: tenant.tenant_id,
              input_snapshot: { score_before: lead.score, bucket_before: lead.bucket },
              output_snapshot: { score_after: coldScore, bucket_after: "cold", reason: "30d_auto_cold" },
              prompt_version: null,
            });
          } catch {
            // Non-fatal.
          }
        }

        await writeTaskExecution({
          run_id,
          tenant_id: tenant.tenant_id,
          agent_id: "score_decay",
          pipeline: "governance",
          status: "success",
        });
      });
    }
  }
);

function recomputeBucket(
  score: number,
  thresholds?: { hot_min?: number; warm_min?: number }
): "hot" | "warm" | "cold" {
  const hot_min = thresholds?.hot_min ?? 80;
  const warm_min = thresholds?.warm_min ?? 55;
  if (score >= hot_min) return "hot";
  if (score >= warm_min) return "warm";
  return "cold";
}
