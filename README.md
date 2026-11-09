# MLX serving on Mac Studio

A local MLX model service on the M1 Ultra Mac Studio. The active backend is
rMLX 0.4.5 with Qwen3.8-27B at 4-bit quantization. Pi is installed globally
through the shared dotsetup recipe; OpenCode remains available. The original
Python vllm-mlx environment is retained for rollback and comparisons.
See [PLAN.md](PLAN.md), [initial results](RESULTS.md),
[OpenCode results](OPENCODE-RESULTS.md) and
[controlled client/server measurements](COMPARISON-RESULTS.md).

## Client direction

The controlled comparison supports trying Pi with rMLX for lower latency, while
keeping OpenCode available. Pi was faster on the same Python backend; rMLX then
removed most repeated-context processing for both clients. Rust did not improve
raw decode speed. See [measured results](COMPARISON-RESULTS.md) for sample sizes,
correctness checks and limitations. Pi Durable remains a separate custom-app
framework option, not a terminal replacement installed by this pilot.

The globally installed OpenCode remains managed by the shared dotsetup recipe.
The project-local Pi and OpenCode copies are diagnostic clients. Existing client
settings are preserved. The user selected and deployed rMLX after the comparison.

## Start and use

On the deployed Mac, rMLX starts at login under `dotsetup.rmlx` and listens on
`http://127.0.0.1:8008/v1`, model `macstudio-local`. It queues requests and runs
one generation at a time. Dotsetup manages the private Tailscale route used by
other machines; the model process itself remains bound to loopback.

Open a terminal in a project and run:

```sh
pi
```

New Pi sessions default to rMLX. OpenAI subscription access is a manually selected
backup, using `openai-codex/gpt-6.1-sol`; it never switches automatically. Sign in
inside Pi with `/login openai-codex`, then use `/model` or Ctrl+P to switch after
login. This OAuth-only provider cannot use an inherited OpenAI API key. Subscription
login and a real cloud response require operator verification on each machine.

Check the Mac service with:

```sh
launchctl print gui/$(id -u)/dotsetup.rmlx
curl --fail http://127.0.0.1:8008/v1/models
```

Do not start a second model process alongside the managed service. If the service
is intentionally stopped, the equivalent foreground command is:

```sh
cd ~/projects/lexlapax/mlx-serve
uv run --frozen python serve_rmlx.py --port 8008
```

OpenCode still uses the same endpoint and remains usable with `opencode`.
[Dotsetup's Pi runbook](https://github.com/lexlapax/dotsetup/blob/main/docs/runbooks/pi-rmlx.md)
owns the shared install, host provider configuration, login service and private
network route. The project-local clients below remain isolated diagnostics.

For the isolated diagnostic client, use:

```sh
uv run --frozen python opencode_client.py
```

For another repository, run `opencode` from its directory. To use the isolated
diagnostic launcher instead:

```sh
cd ~/projects/lexlapax/your-project
~/projects/lexlapax/mlx-serve/.venv/bin/python ~/projects/lexlapax/mlx-serve/opencode_client.py
```

The diagnostic launcher uses private configuration/session directories under
`.runtime/opencode/` and a standalone client server. Read/search operations are
allowed; edits and shell commands ask permission. Other tools are disabled.
Project configuration, plugins and MCP are disabled for this compatibility test;
review repository instructions yourself before approving tool actions. These
permissions are application controls, not an OS sandbox. Global installation
through a shared dotsetup recipe is installed on Mac Studio. The same recipe
covers other hosts; provider settings remain host-specific.

For the project-local Pi diagnostic launcher:

```sh
cd ~/projects/lexlapax/mlx-serve
uv run --frozen python pi.py
```

To work in a different project, keep that project's directory as your working
directory and invoke the launcher by absolute path:

```sh
cd ~/projects/lexlapax/your-project
~/projects/lexlapax/mlx-serve/.venv/bin/python ~/projects/lexlapax/mlx-serve/pi.py
```

Pi configuration and sessions are stored privately under `.runtime/pi-agent/`.
The launcher disables inherited extensions, MCP, skills, context files and
startup network activity. Its model traffic goes to the local endpoint. This
configuration is isolated from the existing Assistant. Pi's file/shell tools
execute on the client machine; the model server does not execute them. Use the
client on a suitable working tree; its tools are not an OS sandbox.

Stop a foreground server with Control-C in its terminal. Stop the managed Mac
service with `launchctl bootout gui/$(id -u)/dotsetup.rmlx`. To run the Python
rollback after stopping Rust, use `uv run --frozen python serve.py`. Stop that
manual Python process before reapplying the Mac host hook to resume managed Rust.

## Reproduce installation

Prerequisites: native arm64 macOS, `uv`, and Node >=22.19.0. The pilot uses the
existing Homebrew Node at `/opt/homebrew/bin/node`, because the shell's older
nvm Node does not meet Pi's requirement. No global npm package is installed.

```sh
cd ~/projects/lexlapax/mlx-serve
uv sync --frozen --python 3.12
PATH=/opt/homebrew/bin:$PATH npm ci --ignore-scripts --no-audit --no-fund
/opt/homebrew/bin/node node_modules/@opencode/cli/postinstall.mjs
uv run --frozen python download.py
uv run --frozen python serve.py --dry-run
```

`uv.lock` and `package-lock.json` pin dependencies. `model.json` pins the full
Hugging Face revision. The downloader uses the standard Hugging Face cache and
stores a local snapshot pointer under `.runtime/`. It does not execute remote
model code or use saved Hugging Face credentials. Model download is about 16 GB;
models, virtual environments, runtime logs and sessions are excluded from Git.

## Verify

With the server running, execute these sequentially:

```sh
cd ~/projects/lexlapax/mlx-serve
uv run --frozen python check_api.py
uv run --frozen python check_pi.py
uv run --frozen python check_opencode.py
uv run --frozen python check_opencode_sessions.py
uv run --frozen python check_opencode_permissions.py
```

The API check covers ordinary/streamed answers, tool-call/result handling,
cancellation recovery, and a 9K-token synthetic context. It records timings in
`.runtime/api-results.json`. The Pi check permits only read/edit tools in a
new disposable fixture, checks exact bytes and runs three Python assertions
separately. OpenCode checks cover the equivalent fixture, persisted session
resume, explicit compaction, and permission decisions. Run its session check
after its fixture check. Raw logs and sessions remain under `.runtime/`.

## Limits and follow-ups

- Pi advertises a 16,384-token context and reserves 2,048 tokens for output.
  Its compaction retains 4,096 recent tokens with a 2,048-token reserve.
  This client context setting is not a server-wide input limit. Full 16K/32K
  sessions and long-running compaction have not been tested.
- The server rejects requested output limits above 2,048 tokens. Its default
  output limit is 1,024; generation is deterministic with thinking disabled.
- `serve.py` sets a 40 GiB MLX allocation limit and a 512 MiB allocator cache
  limit in the server process. These are not an RSS cap or a macOS wired-memory
  change. SimpleEngine does not use the batching GPU-utilization setting.
- The selected hybrid model's text route skips system-prefix KV caching in
  this version. Expect repeated prefill cost on agent turns. The warm timing
  in RESULTS is not evidence of cached conversation prefixes.
- Image inputs, multiple concurrent agents, full-repository coding quality,
  16K/32K input and long-running automatic compaction are untested. OpenCode
  private-server restart/resume and explicit short-session compaction passed.
- Approve login startup/private network deployment only after trying the pilot.
  Host deployment belongs in dotsetup; preserve Herdr's existing Tailscale route.

Source: https://github.com/lexlapax/mlx-serve (public). Runtime state, credentials,
models and test session logs are excluded from Git.


## Explicit Rust pilot

`serve_rmlx.py` checks the reviewed source/model revisions and uses private state.
Its default port is **8009**; `--port 8008` selects the existing client endpoint
only when promoting this backend. Never run both model servers together for this
64 GiB pilot. See [build and rollback](COMPARISON-RESULTS.md).

With the isolated Rust server already running on 8009:

```sh
cd ~/projects/lexlapax/mlx-serve
uv run --frozen python pi.py --backend rmlx
```

This uses a separate `.runtime/pi-agent-rmlx/` configuration/session directory.
Without `--backend rmlx`, Pi uses the current server on 8008 and its existing
private state. The benchmark's automatic fixture edit permissions are not added
to the interactive launcher.
