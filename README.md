# MLX serving on Mac Studio

A native Python service for local chat and coding agents on the M1 Ultra Mac
Studio. The pilot uses vllm-mlx and Qwen3.8-27B at 4-bit quantization, with a
temporary project-local OpenCode and Pi clients. See [PLAN.md](PLAN.md),
[RESULTS.md](RESULTS.md) and [OpenCode results](OPENCODE-RESULTS.md).

## Client direction

OpenCode 2.2.6 now passes the local read/edit/read fixture; restart/resume and manual
compaction and edit/shell permission decisions also passed. See [PLAN.md](PLAN.md). Its project-local installation
is temporary: the requested permanent installation belongs in a shared dotsetup
recipe for all machines, as a globally available CLI. The MLX server is independent
of the coding client. Pi remains the tested fallback below.

## Start and use

The current pilot listens on `http://127.0.0.1:8008/v1` with model ID
`macstudio-local`. It is local-only and has no API authentication. No login job
or Tailscale route is installed. Only one generation runs at a time.

From a Mac Studio terminal, check whether it is already running:

```sh
curl --fail http://127.0.0.1:8008/v1/models
```

If it is not running, start it in a terminal and leave that terminal open:

```sh
cd ~/projects/lexlapax/mlx-serve
uv run --frozen python serve.py
```

Open another terminal for the temporary OpenCode client:

```sh
cd ~/projects/lexlapax/mlx-serve
uv run --frozen python opencode_client.py
```

For another repository, run this launcher from that repository's directory:

```sh
cd ~/projects/lexlapax/your-project
~/projects/lexlapax/mlx-serve/.venv/bin/python ~/projects/lexlapax/mlx-serve/opencode_client.py
```

The pilot uses private configuration/session directories under
`.runtime/opencode/` and a standalone client server. Read/search operations are
allowed; edits and shell commands ask permission. Other tools are disabled.
Project configuration, plugins and MCP are disabled for this compatibility test;
review repository instructions yourself before approving tool actions. These
permissions are application controls, not an OS sandbox. Global installation
through a shared dotsetup recipe for all machines is now authorized and underway.

For the Pi fallback:

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

For a server you started in a terminal, use Control-C in that terminal. For the
pilot left running by the setup session, use `lsof -nP -iTCP:8008 -sTCP:LISTEN`
to find its PID. Inspect `ps -p PID -o command=` and confirm it is this project's
`serve.py` process before running `kill -TERM PID`. Substitute the observed PID;
never reuse a historical PID without checking it.

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
