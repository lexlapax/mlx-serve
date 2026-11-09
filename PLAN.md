# MLX serving pilot on Mac Studio

## User outcome and scope

Run local Apple Silicon inference for coding agents and for general
chat/document work from ~/projects/lexlapax/mlx-serve. Codex is optional.
Hardware: M1 Ultra, 64 GiB unified memory, 48 GPU cores; macOS 26.7.3.
The user approved committing this plan and proceeding with the local pilot on
2026-11-08, including an isolated Python installation and model download.
Later on the same date, the user said OpenCode might be better than Pi and
requested a plan adjustment. OpenCode is now the preferred client to evaluate;
this is a preference for the next trial, not a verified superiority claim.

## Selected approach

Use native arm64 Python 3.12, uv, a project-local .venv and locked dependencies.
Use vllm-mlx with a single 4-bit model through Chat Completions.
Evaluate OpenCode as the primary coding interface. Keep the verified Pi pilot
as a fallback and comparison until OpenCode passes local acceptance.
Keep direct MLX-LM/MLX-VLM available as diagnostic baselines through the same
compatible dependency set. Do not implement another inference engine or proxy.

Installed model: mlx-community/Qwen3.8-27B-4bit with qwen3_xml tool parsing,
pinned in model.json and verified locally with Pi. Keep this model and endpoint
fixed during the client comparison. Upstream published acceptance includes
OpenCode 1.18.31, but it used a different model snapshot and software stack;
current OpenCode 2.x needs a new local test.
Fallback: a supported Qwen coding model if the first candidate cannot be loaded
or cannot complete the test. Record evidence for any change of model or server.

Start on 127.0.0.1:8008 if free, with one active generation, an initial context
budget of 16K tokens and bounded output. Evaluate 32K only after a passing pilot.
Aim to keep total server working memory below 40–44 GiB, leaving desktop room;
this is a planning target, not a verified hard memory cap. Do not raise macOS
wired-memory limits or enable large caches without evidence and review.

## Completed baseline

The plan was committed before installation. Python/MLX dependencies and the
model are pinned, Metal execution passed, and the local API and Pi file-edit
loop passed. RESULTS.md records the actual measurements and limitations.
This evidence remains valid for Pi; it is not evidence of OpenCode acceptance.

## OpenCode trial plan and acceptance

1. Inspect available OpenCode installations and resolve a supported release.
   Pin its exact version and verify native arm64 installation. Prefer a
   project-local installation and runtime state. Confirm the executable's
   actual config schema; do not apply a V1 example to V2 unchanged.
2. Configure a local provider at http://127.0.0.1:8008/v1 with model ID
   macstudio-local and Chat Completions. Explicitly advertise text/tool support,
   16,384 context tokens and at most 2,048 output tokens. Match thinking-disabled
   request settings to the verified server. No additional model download.
3. Isolate config, auth, session and data directories using the pinned release's
   documented controls. Verify effective config, not just a custom config path:
   OpenCode can merge multiple scopes. Disable optional inherited plugins/MCP
   and automatic session publication. Keep auxiliary model calls, including
   title/summary/compaction generation, on this local endpoint. Record any
   remaining startup network activity rather than claiming an offline client.
4. Use one primary agent and one active generation initially. Start with only
   tools needed by the fixture. Tune compaction for the 16K budget: aim to keep
   about 4K recent tokens and reserve room for output and system/tool messages.
   Verify the pinned version's units and behavior. The documented V2 default
   keeps about 15K tokens, so it must not be accepted blindly for this budget.
5. Repeat the existing disposable read/edit/read fixture. Require completed
   streamed tool arguments/results, exact output bytes, successful exit and
   the same three independent Python assertions. Compare prompt token counts,
   total time, retries and failures with Pi's recorded 28.013-second run; one
   run establishes compatibility, not statistically significant performance.
6. Test a short multi-turn session, stop/resume and explicit compaction. Check
   that auxiliary requests stay local and below output limits. For interactive
   project use, configure permissions according to project rules and verify
   file-edit and shell approval behavior with harmless fixture operations.
7. Promote OpenCode to the documented default only when these checks pass.
   Commit its pinned installation, isolated launcher/config, checks and measured
   results. Keep Pi as fallback until the operator has tried OpenCode. If the
   trial fails, record the exact incompatibility and retain the working Pi path.

No client installation or live migration is performed by this plan revision.
The next implementation phase belongs to the assistant. The operator's later
interactive acceptance decides the everyday client. The user has now authorized
committing and pushing progress to the public github.com/lexlapax/mlx-serve repo.

## Why evaluate OpenCode first

OpenCode has built-in configurable agent profiles and resource/action permission
rules, and it supports custom OpenAI-compatible endpoints. Those features make
it a plausible fit for the user's everyday repository work. Pi is already
verified locally and remains the simpler known-working comparison. Neither
client changes the model's weights or guarantees better reasoning or faster
inference. Prompt/tool overhead and compaction behavior must be measured.

Current official docs use V2 `providers`, `package`, `settings` and ordered
`permissions` rules. V1 examples use `provider`, `npm`, `options`, `permission`
and different action names. Context7 returns examples from both generations;
use official version-matched docs and the installed schema to resolve conflicts.

## Installation ownership and rollout

The user clarified that OpenCode must eventually be a globally available CLI
like Codex or Claude, managed by a shared dotsetup recipe for every machine.
This project-local package is only a temporary compatibility fixture. Shared
installation and common client settings belong in dotsetup, with platform
package mappings and host enrollment. They must not depend on an mlx-serve
checkout or on macstudio being the client's host. Mac Studio owns only the MLX
backend. Tailnet access to that backend is a separate deployment step.
The user subsequently resumed shared installation on all machines. Dotsetup now
owns that rollout; this project retains only the isolated compatibility client.

## Deferred deployment

Login startup and authenticated Tailscale access follow pilot acceptance and a
concrete reviewed deployment plan. Preserve the existing Herdr Serve route.
No cloud Assistant replacement, network exposure, sudo changes or launch agent
installation is included in this pilot. Models and caches remain outside Git.

## Alternatives reviewed

- MLX-LM directly: simplest text-only baseline, built-in HTTP API; its server
  documentation cautions about production security.
- MLX-VLM directly: multimodal model loading and APIs, including image inputs.
- oMLX: useful model management and bounded caching; an alternative if those
  operational features outweigh keeping a small CLI-oriented setup.
- Existing vMLX app: installed on this Mac, but not yet validated for this use.
  vMLX and vllm-mlx are separate projects.

## Sources reviewed 2026-11-08

- https://opencode.ai/docs/providers/
- https://opencode.ai/docs/permissions/
- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/config/
- https://opencode.ai/docs/compaction/
- https://github.com/waybarrios/vllm-mlx
- https://github.com/waybarrios/vllm-mlx/blob/main/docs/guides/client-acceptance.md
- https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md
- https://github.com/Neywa-Labs/mlx-vlm
- https://github.com/jundot/omlx
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md
- https://huggingface.co/mlx-community/Qwen3.8-27B-4bit

## Status

Plan revised on 2026-11-08. The MLX API and Pi baseline are installed and verified.
OpenCode 2.2.6 is installed temporarily in this project and passes the streamed
read/edit/read fixture. Private-server restart/resume and manual compaction also passed. Permission
checks passed for rejecting edits, approving edits, and approving a harmless
shell command. The API session busy flag remained set after a rejected edit;
permission results were verified from terminal tool states and fixture bytes.
Pi remains the previously verified comparison.
Login startup and private network access remain deferred until client acceptance.


## Performance follow-up: separate client and backend choices

The operator reported slow interactive OpenCode use and asked about Pi/Pi Durable
and a Rust MLX server as independent alternatives. See
[the researched comparison](CLIENT-SERVER-OPTIONS.md). Recommendation: compare Pi
on the existing server and rMLX with the existing model independently; Pi Durable
is a potential custom persistent-assistant framework, not the immediate client
migration. No alternative server installation or default switch is authorized by
this assessment. Existing working clients/server remain available.


## 2026-11-08 independent comparison outcome

The approved client/server pilot is complete; see COMPARISON-RESULTS.md.
Recommend rMLX for repeated-context serving and Pi for the next interactive trial.
OpenCode remains installed and works against the Rust candidate. Pi Durable stays
out of this terminal pilot. The gain is verified hybrid-context reuse, with cold
prefill unchanged and raw decode slightly slower. Candidate activation on the
existing endpoint is pending the operator's separate choice; login startup and
Tailscale exposure remain deferred.


## Deployment selected

The user approved Pi+rMLX deployment and a shared Pi CLI recipe like OpenCode.
Mac rMLX is now the managed login service on the existing localhost:8008 endpoint;
Python remains a stopped rollback alternative. Pi's standard CLI completed the
read/edit/read fixture with three assertions in 16.548 seconds, selecting the
configured model without command-line model or provider overrides.

Dotsetup owns fleet installation, a private model endpoint, and seeded defaults.
The user explicitly chose a selectable OpenAI subscription backup. The configured
provider is OAuth-only openai-codex, so existing API-key readiness cannot become
paid API fallback. Account login is not assumed and no tokens are transferred.
Windows remains deferred. See dotsetup's Pi rollout for current per-host status.
