/**
 * Inngest function registry
 *
 * Import and export every function here so the API route handler has one
 * place to register them all.
 */

export { pipeline2Onboarding } from "./pipeline2/onboarding";
export { pipeline1DataGather } from "./pipeline1/data-gather";
export { pipeline1LeadProcessor } from "./pipeline1/lead-processor";
export { scoreDecay } from "./scheduled/score-decay";
export { slaMonitor } from "./scheduled/sla-monitor";
export {
  qualityMetricsPerRun,
  qualityMetricsWeekly,
  qualityMetricsMonthly,
} from "./scheduled/quality-metrics";
export { pipeline2RerunCheck } from "./scheduled/pipeline2-rerun-check";
