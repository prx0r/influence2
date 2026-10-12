# Connect AgentRun to my existing agent

First identify the intended harness for this project or workflow from my request, project configuration, and session context. **If the target is Pi, use Path A: the native Pi extension. Otherwise, use Path B: adapters for my existing harness.** An installed `pi` command alone does not select the target; a Codex or Claude Code session may be setting up a Pi project. Ask only if the intended harness is still unclear. State the selected path before installing anything, and follow only that path.

Run an actual AgentRun workflow with **live Jev and my configured agent**. Keep my existing model selection and permitted data access. A scripted demo or a successful installation does not complete this task; verify real decision and agent-step calls.

## Use one release throughout

- Release source and installation: https://github.com/Parcha-ai/agentrun/tree/v0.1.0-beta.2
- Pi package directory: https://pi.dev/packages/@parcha/agentrun-pi
- Pi extension behavior for this release: https://github.com/Parcha-ai/agentrun/blob/v0.1.0-beta.2/packages/pi/README.md
- Repository agent instructions: https://github.com/Parcha-ai/agentrun/blob/v0.1.0-beta.2/docs/agent-instructions.md
- Live support integration: https://github.com/Parcha-ai/agentrun/blob/v0.1.0-beta.2/docs/support-quickstart.md
- Support workflow: https://github.com/Parcha-ai/agentrun/blob/v0.1.0-beta.2/examples/support-answer.mjs
- Website quickstart: https://agentrun.ai/docs/quickstart
- Host integration: https://agentrun.ai/docs/host-integration
- Jev adapter: https://agentrun.ai/docs/jev
- Pi extension and SDK: https://agentrun.ai/docs/pi

AgentRun is public under Apache-2.0. Version `0.1.0-beta.2` of `@parcha/agentrun-dsl`, `@parcha/agentrun-jev`, and `@parcha/agentrun-pi` is published on npm. Use these exact versions and the matching `v0.1.0-beta.2` source tag. Use the release-pinned behavior above even if other documentation describes newer APIs. Requires Node 22.19+ and npm; TypeScript consumers need TypeScript 5.4+.

## 1. Check live prerequisites for the selected harness

Reuse the harness's existing authenticated model. Do not silently choose a different model or provider. For Pi, the extension uses the current Pi model and authentication; no separate AgentRun model configuration is needed.

Check whether the process that will run the workflow has a nonempty `TYPESAFE_API_KEY`. In Path B, an approved server-side secret supplied as `jev.apiKey` is also supported. Check presence only; never print the value. Reuse existing access.

If missing, direct me to https://console.typesafe.ai/keys and https://docs.typesafe.ai/introduction/quickstart. Have me configure the key through the project's secret mechanism or an ignored environment file, not by pasting it into chat. Ensure the running Pi or workflow process loads it; a saved `.env` file needs an explicit loader. A Claude Code, Codex, or Pi login does not authenticate Jev. Continue preparing the workflow while setup is pending, but leave live verification incomplete. Jev is only needed for decision steps; this verification must exercise one.

## 2. Follow the selected setup path

### Path A — Pi: install the native extension

Use the tested Pi host version, 0.87.0. If Pi is not installed, follow the release's Pi installation guide. In my project:

```sh
pi install npm:@parcha/agentrun-pi@0.1.0-beta.2 -l
```

`-l` installs for this project. If Pi is already open, use `/reload`; beta.2 reload clears its current workflow definition. Otherwise start `pi --offline` with credentials loaded. `--offline` skips startup downloads, not model calls. Review Pi's project-trust prompt on first launch, then run `/agentrun status` to check the loaded skill, host version, active model, and Jev configuration. Status makes no provider calls.

**Standard Pi setup needs no AgentRun repository clone, build, or manual `runNode`/`runEffect` adapters. Skip Path B.** Use `/agentrun <task>` to load the packaged author skill. Its model-facing `agentrun` tool must call `action: "describe"` for available tools and configuration, `action: "inspect"` with the complete workflow, then `action: "run"` with input.

Use tools actually supplied by the extension. By default these are active Pi built-ins `read`, `grep`, `find`, and `ls`; the demo `search` tool only reads fictional bundled sources. `help.search` and `support.read` are not installed automatically. Custom extension tools and outer Pi permission hooks are not inherited. A workflow requiring other tools needs explicit host configuration.

Prefer a read-only workflow. Code nodes or active `bash`, `edit`, or `write` require the user to issue `/agentrun run --trusted` for that run; this enables unsandboxed execution and cannot be granted by the model. Follow the pinned Pi guide's tool, permission, and execution limits. Beta.2 workflows remain session-local; do not use unreleased save/load commands.

### Path B — Other harnesses: connect the support workflow

Keep the current harness and connect its real adapters. In the target application:

```sh
npm install --save-exact @parcha/agentrun-dsl@0.1.0-beta.2 @parcha/agentrun-jev@0.1.0-beta.2
```

Use a separate release checkout for the shipped support example; do not change an existing project's branch:

```sh
git clone --branch v0.1.0-beta.2 --single-branch https://github.com/Parcha-ai/agentrun.git
cd agentrun
npm ci --ignore-scripts
npm run build
```

Confirm `git describe --tags --exact-match` reports `v0.1.0-beta.2`. The support files are already in this release; do not replace them with another version. Read `examples/support-answer.mjs`, then copy its template:

```sh
cp examples/support-answer-config.example.mjs support.config.mjs
```

Replace both stubs with actual host adapters:

- `runEffect(params)`: dispatch `help.search` using `params.input.request` and permitted help data. Return `{ text, sources }`; if nothing is found, return `{ text: "", sources: [] }`. Honor cancellation, deadlines, and idempotency.
- `runNode(params)`: call my authenticated agent and forward the full request, including `system`, `user`, `schema`, `tools`, `signal`, and `review` when present. Register read-only `support.read` with the correct account scope. Return `{ text, sources }` directly. A rejected review must continue the same session or fail explicitly.

Keep tools, permissions, model selection, and budgets in the host. The config is trusted server code; keep credentials out of tracked files. Optional `jev` fields are `apiKey`, `baseURL`, `model`, `timeoutMs`, and `maxAttempts`; top-level `timeoutMs` bounds the whole run. The runner constructs the actual `createJevRunner()` and rejects replacement judges or fake transports.

Use the supplied DSL unchanged: find an answer → Jev checks → return it, or investigate once with my agent → Jev rechecks → return or escalate. A nonempty answer with source references, `yes`, and confidence of at least `0.8` passes. This threshold is an example policy, not an accuracy guarantee.

## 3. Run and verify real calls

### If Path A was selected

Use `/agentrun <task>` for my repeatable task. If none was specified, try this real repository task inside Pi:

```text
/agentrun Build and run a workflow that uses an agent to investigate how this repository handles cancellation using the available read-only tools, then asks Jev whether the cited files support the findings. Return the findings or mark the evidence insufficient.
```

Inspect the graph with `/agentrun`; repeat it with `/agentrun run`. Verify an agent step inside the workflow ran, not just the outer Pi authoring conversation, and verify an actual Jev decision ran on the supplied evidence. Use the extension's structured results and events to report what happened. A tools-only workflow, `/agentrun status`, or the scripted demo does not satisfy this check. Missing tools or access must be reported, not replaced by fictional results.

### If Path B was selected

From the checkout with credentials loaded and both adapters implemented:

```sh
npm run demo:support -- payment --config ./support.config.mjs
```

For a local `.env` file:

```sh
node --env-file=.env examples/run-support-answer.mjs payment --config ./support.config.mjs
```

For a request suited to the connected tools, save `{ "request": "Your support question" }` to `request.json`:

```sh
npm run demo:support -- --config ./support.config.mjs --input ./request.json
```

Verify an accepted help answer, an investigation, and an unresolved case. Expected paths are `tool → judge` and `tool → judge → agent → judge`, with escalation when the second check is insufficient. Keep criteria and thresholds fixed; report actual outcomes even when they differ from fixtures.

The CLI reports the workflow digest, observed calls, judgments, and status. It omits request/answer text, source references, and raw provider errors; model and usage may be absent. Exit codes are `0` complete, `2` escalated, and `1` failed. Inspect the answer privately through the host. After testing, expose `runLiveSupport` as a callable host tool where useful, handle escalation, and verify my agent can discover and call it. Sending replies or changing accounts remains a separate host action.

## Optional scripted verification

For Path A, `/agentrun demo` checks the bundled scripted example without model calls. `/agentrun demo live` makes real Pi and Jev calls over fictional bundled sources; it does not replace verification of my authored workflow over real project data. Do not clone a repository just to run the native demo.

For Path B, run these separately to check the support workflow's mechanics:

```sh
npm run demo:support
npm run test:support
```

These fixtures make no live model calls. Password and invoice use zero agent calls and one judgment; payment uses one agent call and two judgments; unresolved does the same and escalates. The all-case demo exits `0`; `npm run demo:support -- unresolved` exits `2`. Do not alter fixture answers merely to force a pass.

## Report the result

State the selected path and installed version, commands run, workflow used, observed tool/Jev/agent-step calls, final status, and any remaining requirements. Separate scripted checks from live verification. Deliver the workflow and any host configuration it required. If access or provider calls are unavailable, say exactly what remains incomplete. Do not claim live success without evidence, disclose credentials or customer data, or invent token, cost, or accuracy improvements. Adapter counts do not measure an agent's internal turns or spending.
