# OpenCode compatibility results, 2026-11-08

OpenCode 2.2.6 passed the bounded local MLX compatibility checks on Mac Studio.
This does not establish real repository coding quality or interactive acceptance.
The package is a temporary project-local test client. Shared globally available
installation belongs in dotsetup and is now authorized for all managed machines.

## Verified

- Read/edit/read fixture completed in 46.687 seconds, with the exact requested
  bytes and three independent Python assertions. Pi took 28.013 seconds in its
  separate single run. This is not a statistical benchmark.
- A private OpenCode server persisted a synthetic marker across server restart.
  The same marker survived explicit compaction. The test lowered keep.tokens to
  256 to compact short history; the ordinary pilot configuration retains 4096.
- Short multi-turn requests with the broader tool set took about 40 seconds each.
  The final configuration exposes fewer tools, but no speed comparison of the
  final configuration is claimed.
- An edit waited for permission. Rejecting it returned a declined tool result
  and left the original file unchanged. Approving it in a new session changed
  exactly the requested text. A harmless touch command also waited for approval
  and created its fixture marker only after approval.
- Config, data, cache and sessions for launcher-driven runs use project-private
  XDG paths. Effective configuration was inspected. The wrapper uses standalone
  mode and explicitly configures local models for primary and auxiliary agents.
  No global user configuration or existing Assistant session was replaced.

## Limitations and test corrections

An initial fixture permission rule used an absolute path where the client matched
relative resources. The filename-scoped test rule fixed that denial. The first
permission checker incorrectly waited for an idle message in persisted history.
After switching to session metadata, a rejected edit still left its busy flag set
through a 180-second timeout. The final test checks terminal tool results and
actual files. This proves enforcement, not that cancellation UI/status is correct.

The final default rules allow read/search, ask for edits/shell/external-directory
access, and deny other tools. They are not an OS sandbox. Tests use disposable
files and temporary server credentials held in memory, never published.

Raw CLI help was invoked before the isolated wrapper was introduced and created
normal client log output; subsequent test runs use private XDG paths. No strict
network isolation trace was collected. Startup catalogs and updates are disabled
for this pilot, and configured model endpoints are local. Request-body override
forwarding was not independently verified; server-side defaults and output
limits remain authoritative.

Automatic long-session compaction, full 16K/32K inputs, concurrent agents,
full-repository work and the interactive approval UI remain untested. The operator
should try the documented launcher in a suitable project before selecting it as
the everyday client. Pi remains available as a verified fallback.

## Evidence

- [File fixture](results/opencode-fixture-2026-11-08.json)
- [Resume and compaction](results/opencode-sessions-2026-11-08.json)
- [Permission decisions](results/opencode-permissions-2026-11-08.json)

Raw events, runtime databases and model weights are ignored. Public Git contains
only source, dependency pins and synthetic aggregate results.

## Installed Mac client follow-up

Dotsetup now seeds a missing Mac user configuration for the installed CLI,
preserving any existing JSON/JSONC settings. The installed server selected the
local agent/model without model or config overrides and passed a separate
slugify task: read/read/edit/read, one approved edit, and six independent Python
assertions. Total time was 80.331 seconds. The test used the permission API;
noninteractive `opencode run` automatically rejects ask permissions. Interactive
UI approval and everyday usability still require operator acceptance.

The disposable runner must set PWD to match its subprocess cwd; normal shell cd
already does this. An initial runner mismatch selected dotsetup instead of the
fixture and was stopped without approving edits. Those attempts are not counted
as successful coding checks. Raw synthetic sessions remain outside Git.

An ordinary installed CLI request from a fresh empty directory returned exactly
MLX READY in 17.395 seconds, with no tool calls or model/server overrides. A prior
request in the coding fixture attempted an unrequested edit before replying;
noninteractive permissions denied it and no file changed. Keep edit/shell approval
controls and assess model behavior during interactive use.

## Reported slowness and direct throughput

The operator reported slow interactive use and an 8.3 tok/s display. A direct
HTTP streaming comparison, bypassing OpenCode, measured:

| Input tokens | Output tokens | First content | Total time | Estimated output rate after first content |
|---:|---:|---:|---:|---:|
| 24 | 128 | 0.658 s | 5.053 s | 28.94 tok/s |
| 4878 | 128 | 30.187 s | 34.768 s | 27.76 tok/s |

These are single sequential samples with synthetic prompts, not peak hardware
benchmarks. Estimated generation rate divides output tokens after the first by
the interval between first and last content chunks. No model, engine or client
configuration was changed. Swap use was zero; server RSS was about 15.6 GiB.

Recent OpenCode model steps produced 40 tokens in 15.82 seconds and 474 in 46.04
seconds. Combined, that is 514 / 61.86 = 8.31 tok/s, matching the reported display.
Upstream V2 TUI code divides turn output by assistant-step time through the end
of streaming, including prompt processing, before tool settlement. That is not
pure token-generation speed. See the [TUI calculation](https://github.com/anomalyco/opencode/blob/dev/packages/tui/src/routes/session/rows.ts).

The active text route logs system-prefix cache skips for non_kv_cache_class,
so growing context is reprocessed on each tool turn. Overlapping requests also
produce serialized-route-busy errors and retries. The direct test attributes
most long-prompt delay to prefill; it does not prove a GPU optimization ceiling.
The current integration needs responsiveness work before acceptance. Next compare
cache-compatible serving options and reduce unnecessary overlapping auxiliary
calls before deciding to change clients or download a smaller model.

[Machine-readable measurements](results/throughput-2026-11-08.json).
