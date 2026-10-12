/** AgentRun workflow runner for influence2.
 *
 * Usage:
 *   node workflows/run.mjs <workflow-name> '<input-json>'
 *   node workflows/run.mjs analytics_review '{"brand":"long-hauls","handle":"@longhauls","channel_id":"UCrntJs4IgQNEPUszDgDoXBg"}'
 *   node workflows/run.mjs content_decide '<input>' 
 *   node workflows/run.mjs release_gate '<input>'
 *   node workflows/run.mjs --validate <workflow-name>   (structure check only)
 *   node workflows/run.mjs --inspect <workflow-name>    (print graph)
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const DSL_DIR = "/root/influence2/.pi/npm/node_modules/@parcha/agentrun-dsl/dist";
const require = createRequire(import.meta.url);
const dsl = require(join(DSL_DIR, "index.js"));
const { runWorkflow, validateWorkflow, inspectWorkflow, formatWorkflowTree } = dsl;
const { deps } = await import("../dash/agentrun_host.mjs");

const [,, cmd, arg] = process.argv;

function loadWorkflow(name) {
  const raw = readFileSync(join(HERE, `${name}.json`), "utf8");
  return JSON.parse(raw);
}

if (cmd === "--validate") {
  const wf = loadWorkflow(arg);
  try {
    await validateWorkflow(wf, undefined, { trusted: true });
    console.log(JSON.stringify({ ok: true, workflow: arg }));
  } catch (e) {
    console.log(JSON.stringify({ ok: false, workflow: arg, error: String(e).slice(0, 1000) }));
    process.exit(1);
  }
  process.exit(0);
}

if (cmd === "--inspect") {
  const wf = loadWorkflow(arg);
  const inspection = inspectWorkflow(wf);
  console.log(formatWorkflowTree(inspection));
  process.exit(0);
}

const wf = loadWorkflow(cmd);
let input = {};
try {
  input = JSON.parse(arg || "{}");
} catch (e) {
  console.error("bad input JSON:", e.message);
  process.exit(1);
}

console.error(`running workflow: ${wf.name}`);
const started = Date.now();
try {
  const result = await runWorkflow(wf, input, deps);
  const ms = Date.now() - started;
  console.log(JSON.stringify({
    status: result.status,
    ms,
    output: result.status === "complete" ? result.output : undefined,
    escalation: result.status === "escalated" ? {
      reason: result.escalation?.reason,
      label: result.escalation?.label,
      kind: result.escalation?.kind,
      stage: result.escalation?.stage,
      state_keys: result.escalation?.state ? Object.keys(result.escalation.state) : [],
    } : undefined,
  }, null, 2));
} catch (e) {
  const ms = Date.now() - started;
  console.error(JSON.stringify({ status: "error", ms, error: String(e).slice(0, 2000) }));
  process.exit(1);
}
