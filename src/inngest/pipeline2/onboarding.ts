/**
 * Pipeline 2 — Tenant Onboarding
 *
 * Runs once per tenant at setup, and again whenever a team lead approves a
 * re-run after significant business-profile changes. Serial by design: every
 * agent's output feeds the next.
 *
 * Stage sequence:
 *   1. pre_flight_check
 *   2. onboarding_agent   (Sonnet)  → PersonaObject
 *   3. icp_agent          (Sonnet)  → IcpDefinition
 *   4. signal_agent       (Sonnet)  → signal[] + detection_rules
 *   5. build_prompt_template        → writes to prompt_registry
 *   6. activate_tenant              → tenant.status = active
 *
 * Crash safety: every step is idempotent. If the function crashes mid-way,
 * Inngest replays it; each step.run() is skipped if its result was already
 * persisted (Inngest memoises step outputs).
 */

import { inngest, Events } from "../client";
import {
  db,
  writeTaskExecution,
  writeLineageRecord,
  updatePipelineRun,
  notifyAdmin,
  notifyTenant,
} from "../../lib/db";
import {
  runOnboardingAgent,
  runIcpAgent,
  runSignalAgent,
  buildPromptTemplate,
} from "../../lib/agents";

export const pipeline2Onboarding = inngest.createFunction(
  {
    id: "pipeline2-onboarding",
    name: "Pipeline 2 — Tenant Onboarding",
    concurrency: {
      // One Pipeline 2 run per tenant at a time.
      // Prevents parallel re-runs from racing on the same persona store.
      key: "event.data.tenant_id",
      limit: 1,
    },
    retries: 0, // Retry logic is explicit per-step below; function-level retry
    //           would replay completed LLM calls and waste money.
  },
  { event: "tenant/onboarding.start" },
  async ({ event, step }) => {
    const {
      tenant_id,
      business_type,
      industry,
      description,
      target_audience,
      geography_focus,
      exclusions,
      trigger,
      rerun_reason,
    } = event.data;

    const run_id = `p2-${tenant_id}-${Date.now()}`;

    // ── 1. Pre-flight check ────────────────────────────────────────────────────
    await step.run("pre_flight_check", async () => {
      const tenant = await db.tenants.findOne(tenant_id);
      if (!tenant) throw new Error(`Tenant ${tenant_id} not found`);
      if (tenant.status === "suspended" || tenant.status === "churned") {
        throw new Error(`Tenant ${tenant_id} is ${tenant.status}; aborting Pipeline 2`);
      }

      await db.pipeline_runs.create({
        run_id,
        tenant_id,
        pipeline: "onboarding",
        status: "running",
        trigger,
        started_at: new Date().toISOString(),
      });

      await writeTaskExecution({
        run_id,
        tenant_id,
        agent_id: "pre_flight_check",
        pipeline: "onboarding",
        status: "success",
      });
    });

    // ── 2. Onboarding Agent — generates PersonaObject ─────────────────────────
    const personaObject = await step.run("onboarding_agent", async () => {
      const startMs = Date.now();
      let attempt = 0;

      while (attempt < 2) {
        try {
          const persona = await runOnboardingAgent({
            tenant_id,
            business_type,
            industry,
            description,
            target_audience,
            geography_focus,
            exclusions,
          });

          // Validate: scoring_weights must sum to 1.0
          const weightSum = Object.values(persona.scoring_weights).reduce(
            (a, b) => a + b,
            0
          );
          if (Math.abs(weightSum - 1.0) > 0.001) {
            throw new Error(
              `Onboarding Agent: scoring_weights sum to ${weightSum}, expected 1.0`
            );
          }

          await db.personas.upsert({ tenant_id, ...persona });

          await writeLineageRecord({
            run_id,
            lead_id: null,
            agent_id: "onboarding_agent",
            tenant_id,
            input_snapshot: { business_type, industry, description },
            output_snapshot: persona,
            prompt_version: persona.prompt_version,
          });

          await writeTaskExecution({
            run_id,
            tenant_id,
            agent_id: "onboarding_agent",
            pipeline: "onboarding",
            status: "success",
            duration_ms: Date.now() - startMs,
            retry_count: attempt,
          });

          return persona;
        } catch (err) {
          attempt++;
          if (attempt >= 2) {
            await writeTaskExecution({
              run_id,
              tenant_id,
              agent_id: "onboarding_agent",
              pipeline: "onboarding",
              status: "failure",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
              error: String(err),
            });
            await notifyAdmin({ tenant_id, step: "onboarding_agent", error: err });
            await notifyTenant({
              tenant_id,
              message: "Scoring setup failed at business profile analysis. Please review your submitted information.",
            });
            throw err;
          }
        }
      }
      throw new Error("unreachable");
    });

    // ── 3. ICP Agent — generates IcpDefinition ────────────────────────────────
    const icpDefinition = await step.run("icp_agent", async () => {
      const startMs = Date.now();
      let attempt = 0;

      while (attempt < 2) {
        try {
          const icp = await runIcpAgent({ tenant_id, persona: personaObject });

          await db.ideal_customer_profiles.upsert({ tenant_id, ...icp });
          await db.ideal_customer_profile_versions.create({
            tenant_id,
            icp_definition: icp,
            created_at: new Date().toISOString(),
          });

          await writeLineageRecord({
            run_id,
            lead_id: null,
            agent_id: "icp_agent",
            tenant_id,
            input_snapshot: { persona_version: personaObject.version },
            output_snapshot: icp,
            prompt_version: icp.prompt_version,
          });

          await writeTaskExecution({
            run_id,
            tenant_id,
            agent_id: "icp_agent",
            pipeline: "onboarding",
            status: "success",
            duration_ms: Date.now() - startMs,
            retry_count: attempt,
          });

          return icp;
        } catch (err) {
          attempt++;
          if (attempt >= 2) {
            await writeTaskExecution({
              run_id,
              tenant_id,
              agent_id: "icp_agent",
              pipeline: "onboarding",
              status: "failure",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
              error: String(err),
            });
            await notifyAdmin({ tenant_id, step: "icp_agent", error: err });
            await notifyTenant({
              tenant_id,
              message: "Scoring setup failed at ICP definition. Please review your business profile.",
            });
            throw err;
          }
        }
      }
      throw new Error("unreachable");
    });

    // ── 4. Signal Agent — generates signal[] + detection_rules ────────────────
    const signalDefinitions = await step.run("signal_agent", async () => {
      const startMs = Date.now();
      let attempt = 0;

      while (attempt < 2) {
        try {
          const signals = await runSignalAgent({
            tenant_id,
            persona: personaObject,
            icp: icpDefinition,
          });

          // Validate: each signal must have a valid detection_rule.type
          for (const sig of signals) {
            if (!sig.detection_rule?.type) {
              throw new Error(`Signal "${sig.name}" missing detection_rule.type`);
            }
          }

          await db.signals.bulkUpsert(
            signals.map((s) => ({ tenant_id, ...s }))
          );

          await writeLineageRecord({
            run_id,
            lead_id: null,
            agent_id: "signal_agent",
            tenant_id,
            input_snapshot: {
              persona_version: personaObject.version,
              icp_id: icpDefinition.icp_id,
            },
            output_snapshot: { signal_count: signals.length, signals },
            prompt_version: null,
          });

          await writeTaskExecution({
            run_id,
            tenant_id,
            agent_id: "signal_agent",
            pipeline: "onboarding",
            status: "success",
            duration_ms: Date.now() - startMs,
            retry_count: attempt,
          });

          return signals;
        } catch (err) {
          attempt++;
          if (attempt >= 2) {
            await writeTaskExecution({
              run_id,
              tenant_id,
              agent_id: "signal_agent",
              pipeline: "onboarding",
              status: "failure",
              duration_ms: Date.now() - startMs,
              retry_count: attempt,
              error: String(err),
            });
            await notifyAdmin({ tenant_id, step: "signal_agent", error: err });
            await notifyTenant({
              tenant_id,
              message: "Scoring setup failed at signal definitions. Please contact support.",
            });
            throw err;
          }
        }
      }
      throw new Error("unreachable");
    });

    // ── 5. Build prompt template ───────────────────────────────────────────────
    const promptVersion = await step.run("build_prompt_template", async () => {
      const template = await buildPromptTemplate({
        tenant_id,
        persona: personaObject,
        icp: icpDefinition,
        signals: signalDefinitions,
      });

      await db.prompt_registry.upsert({
        tenant_id,
        ...template,
        created_at: new Date().toISOString(),
      });

      await writeTaskExecution({
        run_id,
        tenant_id,
        agent_id: "build_prompt_template",
        pipeline: "onboarding",
        status: "success",
      });

      return template.version;
    });

    // ── 6. Activate tenant ────────────────────────────────────────────────────
    await step.run("activate_tenant", async () => {
      // Only flip to active if the tenant has at least one active channel_connection.
      // (The readiness check from onboarding-flow-readiness analysis.)
      const activeConnectors = await db.channel_connections.count({
        tenant_id,
        status: "active",
      });

      if (activeConnectors === 0) {
        // Pipeline 2 is done; tenant can't activate yet — no connectors.
        // Status stays "onboarding". The UI will poll and show the connector
        // prompt. Activation fires again when a connector goes live.
        await updatePipelineRun(run_id, {
          status: "complete",
          ended_at: new Date().toISOString(),
          note: "Pipeline 2 complete; waiting for first active connector before activation",
        });
        await inngest.send({
          name: "tenant/pipeline2.complete",
          data: {
            tenant_id,
            persona_version: personaObject.version,
            signal_version: signalDefinitions[0]?.version ?? "v1",
          },
        });
        return;
      }

      // Both conditions met → activate.
      await db.tenants.update(tenant_id, {
        status: "active",
        activated_at: new Date().toISOString(),
      });

      // Drain the queue: score any leads that arrived during onboarding gap.
      const capturedLeads = await db.leads.findAll({
        tenant_id,
        pipeline_stage: "captured",
      });

      for (const lead of capturedLeads) {
        await inngest.send({
          name: "lead/received",
          data: {
            tenant_id,
            run_id: `p1-${tenant_id}-drain-${Date.now()}`,
            lead_id: lead.lead_id,
            entry_point: lead.entry_point,
            raw_payload: lead.raw_payload,
            channel: lead.channel,
          },
        });
      }

      await updatePipelineRun(run_id, {
        status: "complete",
        ended_at: new Date().toISOString(),
      });

      await inngest.send({
        name: "tenant/pipeline2.complete",
        data: {
          tenant_id,
          persona_version: personaObject.version,
          signal_version: signalDefinitions[0]?.version ?? "v1",
        },
      });

      await notifyTenant({
        tenant_id,
        message: "Your platform is ready. Leads are now being scored.",
      });
    });
  }
);
