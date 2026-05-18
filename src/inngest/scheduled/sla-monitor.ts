/**
 * SLA Breach Monitor — Hourly Scheduled Job
 *
 * Enforces the action-sla concept:
 *   HOT  — salesperson must contact within 24 hours
 *   WARM — contact within 2–3 days
 *   COLD — weekly nurture (no SLA alert; monitored separately)
 *
 * Checks hourly; alerts the team lead when a deadline is breached.
 * Alert delivery channel: configured per-tenant in tenant_config.alert_channel.
 */

import { inngest } from "../client";
import { db, notifyTeamLead } from "../../lib/db";

export const slaMonitor = inngest.createFunction(
  {
    id: "sla-monitor",
    name: "SLA Breach Monitor — Hourly",
    concurrency: { limit: 1 },
  },
  { cron: "0 * * * *" }, // Every hour on the hour
  async ({ step }) => {
    const now = new Date();

    const tenants = await step.run("load_active_tenants", async () => {
      return db.tenants.findAll({ status: "active" });
    });

    for (const tenant of tenants) {
      await step.run(`sla_check_tenant_${tenant.tenant_id}`, async () => {
        // Find HOT and WARM leads past their SLA deadline with no sales touch recorded.
        const breachedLeads = await db.leads.findAll({
          tenant_id: tenant.tenant_id,
          pipeline_stage: "delivered",
          bucket_in: ["hot", "warm"],
          sla_deadline_before: now.toISOString(),
          first_contact_at: null, // No contact recorded yet.
          sla_alerted: false,     // Don't re-alert on the same breach.
        });

        if (breachedLeads.length === 0) return;

        const hotBreaches = breachedLeads.filter((l: { bucket: string }) => l.bucket === "hot");
        const warmBreaches = breachedLeads.filter((l: { bucket: string }) => l.bucket === "warm");

        // Alert the team lead with a summary.
        await notifyTeamLead({
          tenant_id: tenant.tenant_id,
          alert_type: "sla_breach",
          summary: {
            hot_breaches: hotBreaches.length,
            warm_breaches: warmBreaches.length,
            leads: breachedLeads.map((l: { lead_id: string; bucket: string; sla_deadline: string; score: number }) => ({
              lead_id: l.lead_id,
              bucket: l.bucket,
              sla_deadline: l.sla_deadline,
              score: l.score,
            })),
          },
          channel: tenant.tenant_config.alert_channel ?? "chat",
        });

        // Mark leads as alerted to prevent duplicate alerts.
        for (const lead of breachedLeads) {
          await db.leads.update(lead.lead_id, { sla_alerted: true });
        }

        // Write to alert_incident entity for governance observability.
        for (const lead of breachedLeads) {
          await db.alert_incidents.create({
            tenant_id: tenant.tenant_id,
            lead_id: lead.lead_id,
            alert_type: "sla_breach",
            bucket: lead.bucket,
            sla_deadline: lead.sla_deadline,
            detected_at: now.toISOString(),
          });
        }
      });
    }
  }
);
