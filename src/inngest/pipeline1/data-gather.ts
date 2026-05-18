/**
 * Pipeline 1 — Data Gather
 *
 * Entry point for every Pipeline 1 run (webhook, schedule, or chat trigger).
 * Responsibilities:
 *   1. Pre-flight check (tenant active, signal_definitions + prompt_template exist)
 *   2. Fetch leads from all active channels in parallel
 *   3. Deduplicate (phone → email → name+location)
 *   4. Fan out: fire one "lead/received" event per unique lead
 *
 * DM events (WhatsApp / Facebook DM / Instagram DM) enter at Step 0 of lead-processor.
 * Lead Ad events enter at Step 3 (skip Pre-Filter Gate and Message Parser).
 *
 * Channel failure policy:
 *   - One channel fails → log, alert admin, continue with remaining channels.
 *   - All channels fail → halt run, notify user.
 */

import { inngest } from "../client";
import {
  db,
  writeTaskExecution,
  updatePipelineRun,
  notifyAdmin,
} from "../../lib/db";
import { fetchLeadsFromChannel, deduplicateLeads } from "../../lib/ingestion";

export const pipeline1DataGather = inngest.createFunction(
  {
    id: "pipeline1-data-gather",
    name: "Pipeline 1 — Data Gather",
    concurrency: {
      // One active Pipeline 1 run per tenant at a time at this entry point.
      // Prevents scheduling two full batch runs simultaneously.
      key: "event.data.tenant_id",
      limit: 1,
    },
  },
  { event: "lead/batch.trigger" },
  async ({ event, step }) => {
    const { tenant_id, run_id, trigger_type, source_list } = event.data;

    // ── 1. Pre-flight check ────────────────────────────────────────────────────
    await step.run("pre_flight_check", async () => {
      const tenant = await db.tenants.findOne(tenant_id);

      if (!tenant || tenant.status !== "active") {
        throw new Error(
          `Tenant ${tenant_id} is not active (status: ${tenant?.status ?? "not found"}). Complete onboarding first.`
        );
      }

      const hasSignals = await db.signals.exists({ tenant_id });
      const hasPrompt = await db.prompt_registry.exists({ tenant_id });

      if (!hasSignals || !hasPrompt) {
        throw new Error(
          `Pipeline 2 not complete for tenant ${tenant_id}: ` +
            `signals=${hasSignals}, prompt=${hasPrompt}`
        );
      }

      await db.pipeline_runs.create({
        run_id,
        tenant_id,
        pipeline: "lead_processing",
        status: "running",
        trigger: trigger_type,
        started_at: new Date().toISOString(),
      });
    });

    // ── 2. Fetch from all channels in parallel (12-second per-source timeout) ─
    const channelResults = await step.run("fetch_all_channels", async () => {
      const activeConnectors = await db.channel_connections.findAll({
        tenant_id,
        status: "active",
      });

      if (activeConnectors.length === 0) {
        throw new Error(`No active channel connectors for tenant ${tenant_id}`);
      }

      const CHANNEL_TIMEOUT_MS = 12_000;
      const results = await Promise.allSettled(
        activeConnectors
          .filter((c) => source_list.includes(c.channel_type))
          .map((connector) =>
            Promise.race([
              fetchLeadsFromChannel(connector),
              new Promise<never>((_, reject) =>
                setTimeout(
                  () => reject(new Error(`${connector.channel_type} timed out`)),
                  CHANNEL_TIMEOUT_MS
                )
              ),
            ])
          )
      );

      const leads: Array<{
        raw_payload: Record<string, unknown>;
        channel: string;
        entry_point: "dm" | "lead_ad";
      }> = [];

      let successCount = 0;

      for (const [i, result] of results.entries()) {
        const connector = activeConnectors[i];
        if (result.status === "fulfilled") {
          leads.push(...result.value);
          successCount++;
        } else {
          await notifyAdmin({
            tenant_id,
            step: `fetch_${connector.channel_type}`,
            error: result.reason,
          });
          await writeTaskExecution({
            run_id,
            tenant_id,
            agent_id: `fetch_${connector.channel_type}`,
            pipeline: "lead_processing",
            status: "failure",
            error: String(result.reason),
          });
        }
      }

      if (successCount === 0) {
        throw new Error(
          `All ${activeConnectors.length} channel fetches failed for tenant ${tenant_id}`
        );
      }

      await writeTaskExecution({
        run_id,
        tenant_id,
        agent_id: "fetch_all_channels",
        pipeline: "lead_processing",
        status: "success",
      });

      return leads;
    });

    // ── 3. Deduplication ──────────────────────────────────────────────────────
    const uniqueLeads = await step.run("deduplicate", async () => {
      // Dedup order: phone first → email → name+location
      const deduped = deduplicateLeads(channelResults);

      await writeTaskExecution({
        run_id,
        tenant_id,
        agent_id: "deduplicate",
        pipeline: "lead_processing",
        status: "success",
      });

      return deduped;
    });

    // ── 4. Fan out — one event per lead ───────────────────────────────────────
    // Inngest handles the fan-out; each lead gets its own isolated run of
    // pipeline1-lead-processor with independent retries.
    await step.sendEvent(
      "fan_out_leads",
      uniqueLeads.map((lead) => ({
        name: "lead/received" as const,
        data: {
          tenant_id,
          run_id,
          lead_id: `lead-${tenant_id}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          entry_point: lead.entry_point,
          raw_payload: lead.raw_payload,
          channel: lead.channel as Events["lead/received"]["data"]["channel"],
        },
      }))
    );

    await updatePipelineRun(run_id, {
      leads_dispatched: uniqueLeads.length,
    });
  }
);

// Import Events type for the sendEvent call above
import type { Events } from "../client";
