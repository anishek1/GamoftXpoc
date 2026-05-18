import { Inngest } from "inngest";

export const inngest = new Inngest({ id: "lead-intelligence-engine" });

// ─── Event catalogue ──────────────────────────────────────────────────────────
// Every event fired anywhere in the system is typed here.
// Events follow: domain/action pattern (e.g. "tenant/onboarding.start")

export type Events = {
  // Pipeline 2 – onboarding
  "tenant/onboarding.start": {
    data: {
      tenant_id: string;
      business_type: "B2B" | "B2C" | "Hybrid";
      industry: string;
      description: string;
      target_audience: string;
      geography_focus: string;
      exclusions: string;
      trigger: "initial_setup" | "team_lead_approved_rerun";
      rerun_reason?: string;
    };
  };
  "tenant/pipeline2.complete": {
    data: { tenant_id: string; persona_version: string; signal_version: string };
  };

  // Pipeline 1 – lead processing
  "lead/batch.trigger": {
    data: {
      tenant_id: string;
      trigger_type: "webhook" | "schedule" | "chat";
      run_id: string;
      source_list: string[];
    };
  };
  "lead/received": {
    data: {
      tenant_id: string;
      run_id: string;
      lead_id: string;
      entry_point: "dm" | "lead_ad"; // DM = Step 0, Lead Ad = Step 3
      raw_payload: Record<string, unknown>;
      channel: "whatsapp" | "facebook" | "instagram" | "website" | "linkedin";
    };
  };
  "lead/clarification.received": {
    data: { tenant_id: string; lead_id: string; reply_text: string };
  };
  "pipeline/run.complete": {
    data: {
      tenant_id: string;
      run_id: string;
      leads_total: number;
      leads_scored: number;
      leads_human_review: number;
      leads_failed: number;
    };
  };

  // Governance
  "feedback/outcome.recorded": {
    data: {
      tenant_id: string;
      lead_id: string;
      outcome: "converted" | "not_converted" | "disqualified";
      recorded_by: string;
    };
  };
};
