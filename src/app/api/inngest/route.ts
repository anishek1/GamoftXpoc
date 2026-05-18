/**
 * Inngest HTTP endpoint — Next.js App Router
 *
 * Inngest polls this endpoint to discover registered functions and delivers
 * events to them. All functions are registered once here.
 *
 * In production: set INNGEST_SIGNING_KEY and INNGEST_EVENT_KEY in env.
 * In development: run `npx inngest-cli@latest dev` to get a local dev server.
 */

import { serve } from "inngest/next";
import { inngest } from "../../../inngest/client";
import * as functions from "../../../inngest";

export const { GET, POST, PUT } = serve({
  client: inngest,
  functions: Object.values(functions),
});
