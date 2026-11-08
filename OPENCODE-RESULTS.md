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
