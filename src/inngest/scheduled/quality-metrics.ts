/**
 * Quality Metrics — Three Scheduled Jobs
 *
 * Implements the governance quality tracking cadence from orchestration-layer-spec §5:
 *
 *   Per-run  (fires at end of every Pipeline 1 run via "pipeline/run.complete" event)
 *     → Score Coverage Rate, Confidence bands, Bucket distribution,
 *       Pipeline failures, Human review rate
 *
 *   Weekly   (Monday 00:00 UTC)
 *     → AR1 SLA Compliance, AR2 Action Rate, AR3 Time-to-Action,
 *       AR4 Action Types, C1 Bucket Stability, C2 Score Drift
 *
 *   Monthly  (1st of each month, 01:00 UTC — requires ≥100 outcomes per bucket)
 *     → AP1 Bucket Outcome Rate, AP2 Discrimination Ratio,
 *       AP3 Completeness Qualifier, C4 Decay-Rescore Coherence, AR5 Priority Alignment
 *
 * Rule: quality metric jobs read from quality_snapshots only.
 * They never query pipeline_log, leads, or lineage_record directly in hot queries
 * (those tables are being written to by Pipeline 1 at the same time).
 * Pre-aggregated counts are read from materialized data via db.quality_snapshots.
 *
 * Rule: governance failure must never halt Pipeline 1 or Pipeline 2.
 */

import { inngest } from "../client";
import { db } from "../../lib/db";
import { computePerRunMetrics, computeWeeklyMetrics, computeMonthlyMetrics } from "../../lib/metrics";

// ─── 1. Per-Run metrics ───────────────────────────────────────────────────────

export const qualityMetricsPerRun = inngest.createFunction(
  {
    id: "quality-metrics-per-run",
    name: "Quality Metrics — Per Run",
    // Non-fatal: if this function fails it must not affect Pipeline 1.
    retries: 2,
  },
  { event: "pipeline/run.complete" },
  async ({ event, step }) => {
    const {
      tenant_id,
      run_id,
      leads_total,
      leads_scored,
      leads_human_review,
      leads_failed,
    } = event.data;

    await step.run("compute_per_run_metrics", async () => {
      const metrics = await computePerRunMetrics({
        tenant_id,
        run_id,
        leads_total,
        leads_scored,
        leads_human_review,
        leads_failed,
      });

      // Write to quality_snapshots — this is the ONLY write destination.
      // No dashboard or API ever queries raw pipeline tables directly.
      await db.quality_snapshots.bulkCreate(
        Object.entries(metrics).map(([metric_name, value]) => ({
          tenant_id,
          run_id,
          metric_name,
          value,
          cadence: "per_run",
          computed_at: new Date().toISOString(),
        }))
      );

      // Alert engineering lead if Score Coverage Rate drops below threshold.
      const coverageRate = metrics["score_coverage_rate"];
      if (coverageRate !== undefined && coverageRate < 0.9) {
        await db.alert_incidents.create({
          tenant_id,
          run_id,
          alert_type: "low_score_coverage",
          value: coverageRate,
          threshold: 0.9,
          detected_at: new Date().toISOString(),
        });
      }

      // Alert if >50% of leads fall below 50% completeness (enrichment failing).
      const completenessDistribution = metrics["lead_completeness_below_50pct_rate"];
      if (completenessDistribution !== undefined && completenessDistribution > 0.5) {
        await db.alert_incidents.create({
          tenant_id,
          run_id,
          alert_type: "enrichment_completeness_warning",
          value: completenessDistribution,
          threshold: 0.5,
          detected_at: new Date().toISOString(),
        });
      }
    });
  }
);

// ─── 2. Weekly metrics ────────────────────────────────────────────────────────

export const qualityMetricsWeekly = inngest.createFunction(
  {
    id: "quality-metrics-weekly",
    name: "Quality Metrics — Weekly",
    retries: 2,
  },
  { cron: "0 0 * * 1" }, // Monday at 00:00 UTC
  async ({ step }) => {
    const tenants = await step.run("load_active_tenants", async () => {
      return db.tenants.findAll({ status: "active" });
    });

    for (const tenant of tenants) {
      await step.run(`weekly_metrics_tenant_${tenant.tenant_id}`, async () => {
        const weekEnd = new Date();
        const weekStart = new Date();
        weekStart.setDate(weekStart.getDate() - 7);

        const metrics = await computeWeeklyMetrics({
          tenant_id: tenant.tenant_id,
          window_start: weekStart.toISOString(),
          window_end: weekEnd.toISOString(),
        });

        // AR1–AR4, C1–C2 → quality_snapshots
        await db.quality_snapshots.bulkCreate(
          Object.entries(metrics).map(([metric_name, value]) => ({
            tenant_id: tenant.tenant_id,
            run_id: null,
            metric_name,
            value,
            cadence: "weekly",
            window_start: weekStart.toISOString(),
            window_end: weekEnd.toISOString(),
            computed_at: new Date().toISOString(),
          }))
        );

        // Compute Global KPIs and write to slo_measurements:
        //   System Health = Pipeline Coverage (avg Score Coverage Rate) + Score Stability (avg C1)
        const systemHealth = {
          pipeline_coverage: metrics["score_coverage_rate_avg_all_tenants"],
          score_stability: metrics["c1_bucket_stability_avg_all_tenants"],
        };

        await db.slo_measurements.create({
          tenant_id: tenant.tenant_id,
          kpi_name: "system_health",
          pipeline_coverage: systemHealth.pipeline_coverage,
          score_stability: systemHealth.score_stability,
          measured_at: weekEnd.toISOString(),
        });
      });
    }
  }
);

// ─── 3. Monthly metrics ───────────────────────────────────────────────────────

export const qualityMetricsMonthly = inngest.createFunction(
  {
    id: "quality-metrics-monthly",
    name: "Quality Metrics — Monthly",
    retries: 2,
  },
  { cron: "0 1 1 * *" }, // 1st of every month at 01:00 UTC
  async ({ step }) => {
    const tenants = await step.run("load_active_tenants", async () => {
      return db.tenants.findAll({ status: "active" });
    });

    for (const tenant of tenants) {
      await step.run(`monthly_metrics_tenant_${tenant.tenant_id}`, async () => {
        const monthEnd = new Date();
        const monthStart = new Date();
        monthStart.setMonth(monthStart.getMonth() - 1);

        // Monthly metrics require ≥100 outcomes per bucket.
        const outcomeCounts = await db.feedback_records.countByBucket({
          tenant_id: tenant.tenant_id,
          after: monthStart.toISOString(),
        });

        const hasEnoughData = Object.values(outcomeCounts).every(
          (count) => (count as number) >= 100
        );

        if (!hasEnoughData) {
          // Not enough outcome data — skip AP1/AP2 (need Month 1 baseline first).
          await db.quality_snapshots.create({
            tenant_id: tenant.tenant_id,
            metric_name: "monthly_metrics_skipped_insufficient_outcomes",
            value: 1,
            cadence: "monthly",
            computed_at: new Date().toISOString(),
            note: "Fewer than 100 outcomes per bucket; AP1/AP2 deferred",
          });
          return;
        }

        const metrics = await computeMonthlyMetrics({
          tenant_id: tenant.tenant_id,
          window_start: monthStart.toISOString(),
          window_end: monthEnd.toISOString(),
          outcome_counts: outcomeCounts as Record<string, number>,
        });

        // AP1–AP3, C4, AR5 → quality_snapshots
        await db.quality_snapshots.bulkCreate(
          Object.entries(metrics).map(([metric_name, value]) => ({
            tenant_id: tenant.tenant_id,
            run_id: null,
            metric_name,
            value,
            cadence: "monthly",
            window_start: monthStart.toISOString(),
            window_end: monthEnd.toISOString(),
            computed_at: new Date().toISOString(),
          }))
        );

        // Global KPIs for Business Health and Tenant Health Rate:
        //   Business Health = Scoring Lift (AP2 Discrimination Ratio) + HOT Response Rate (AR1)
        await db.slo_measurements.create({
          tenant_id: tenant.tenant_id,
          kpi_name: "business_health",
          discrimination_ratio: metrics["ap2_discrimination_ratio"],
          hot_sla_compliance: metrics["ar1_hot_sla_compliance"],
          measured_at: monthEnd.toISOString(),
        });
      });
    }
  }
);
