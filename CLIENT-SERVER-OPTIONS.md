# Independent client and server evaluations

Research date: 2026-11-08. The user asked whether Pi or Pi Durable could replace
OpenCode, independently of replacing the Python MLX server with a Rust server.
This is an assessment and proposed comparison, not approval to install or switch.

## Recommendation

Compare ordinary Pi against OpenCode on the current server, then compare rMLX
against the current server with the same client and model. Combine the winners
only after both measurements. Keep Pi Durable as a separate option for building
a persistent assistant, rather than treating it as a faster Pi terminal client.

## Why this fits the measured problem

The local server generates about 28-29 output tokens/s after the first content
chunk. A synthetic 4878-token prompt took 30.187 seconds to first content. Current
SimpleEngine text requests skip system-prefix caching for the hybrid cache type.
Overlapping requests have also produced busy errors and retries. We need less
repeated prompt processing and predictable queuing, not merely a new language.

Pi's earlier read/edit/read fixture took 28.013 seconds versus OpenCode's 46.687.
Those were individual compatibility runs, not a repeated controlled benchmark
or evidence of superior coding quality. Pi cannot restore a cache the server
never retains. Both client and backend work remain relevant.

## Client options

**Pi coding agent:** the practical immediate comparison. It supplies a terminal
interface, CLI/RPC/SDK entry points and extensible tools. The pinned 1.5.0 local
pilot already works against this MLX endpoint. Compare actual prompt size and
model-call count with matching tools, context and output budget. Preserve required
edit/shell approval behavior when moving beyond disposable fixtures.

**Pi Durable:** an experimental application framework, not a replacement terminal
app. It provides persisted conversations/tasks and recovery across process
failure, with SQLite and other storage choices. It fits a future assistant that
must resume unattended work or accept several interfaces. We would own the UI,
resource loading, permissions and execution policy. Its model/session affinity
can help a capable provider retain context, but does not implement the model
server's GPU prompt cache. Background compaction and concurrent conversations
would need to respect our single-generation backend.

Sources:
- https://pi.dev/
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md
- https://earendil.com/posts/pi-durable/
- https://github.com/earendil-works/pi/blob/main/packages/durable/README.md

## Rust server options

**rMLX, first candidate:** native Rust serving through MLX/mlx-c, OpenAI-compatible
streaming and tools. Its README lists Qwen3.8-27B-4bit as a test target. Our pinned
snapshot declares Qwen3_5ForConditionalGeneration and affine 4-bit, group size 64;
the model reference explicitly routes that dense hybrid architecture through its
Qwen3.5 implementation. This supports trying the existing snapshot, not a claim
that our exact revision is locally verified in rMLX.

Its cache design preserves both attention K/V and recurrent state. It documents
strict-prefix reuse and an internal anchor for changed chat-template tails. This
addresses the architectural complication that disables our current cache path.
Not every architecture or prompt change gets the same reuse; measure actual hits
and repeat-turn correctness, not just a warm identical prompt.

Its server uses one generation permit with FIFO waiting and bounded admission.
There is no continuous batching. That is a plausible improvement over the busy
errors observed here, not a promise of parallel throughput. Cache slots, context,
output and memory limits must be explicit in the pilot.

The published performance anchors use an M5 Max and other model snapshots. They
cannot predict our M1 Ultra. M5 Neural Accelerator-specific benefits do not apply
to this Mac. Rust alone does not establish faster decode: rMLX still relies on
native MLX operations, and Python-facing MLX already executes GPU operations
natively. Model correctness and measured latency decide the migration.

**Velox, secondary:** a Rust/Metal server with MLX-format weights and claims of
batching and caching. Its published comparison uses Qwen3-0.6B on an M2 Max, and
shows lower single-user throughput than its Ollama comparator. That is weak
validation for our hybrid 27B model. rMLX documents a closer model/cache match.

Sources:
- https://github.com/Pushkinist/rMLX
- https://github.com/Pushkinist/rMLX/blob/main/docs/MODELS.md
- https://github.com/Pushkinist/rMLX/blob/main/docs/PROMPT_CACHE.md
- https://github.com/Pushkinist/rMLX/blob/main/docs/SERVER.md
- https://github.com/Pushkinist/rMLX/blob/main/docs/PERF_BASELINE.md
- https://github.com/Soflutionltd/velox/blob/main/README.md

## Proposed bounded comparison

1. Repeat Pi and OpenCode with the existing model/server. Use the same repository
   fixture, initial content, permissions, output cap and acceptance assertions.
   Record prompt tokens, model-call count, first-content latency, total task time
   and failures over at least three runs.
2. Pin a reviewed rMLX commit and compatible native MLX dependencies. Reuse the
   existing model snapshot. Preserve the current environment and rollback command.
   Run on loopback; benchmark servers sequentially to avoid GPU contention and
   duplicated model residency on the 64 GiB Mac.
3. Test direct short and 5K/9K prompts, then repeated and appended-context turns.
   Require evidence of cache hits and correct continuation. Measure cold/warm
   first-content latency, decode rate, memory and cancellation recovery. Test two
   overlapping requests and tool-call/result streams, not just raw text.
4. Test the winning client/server combination on the coding fixture and an
   interactive task. Suggested success target: at least halve repeated-context
   first-content latency without breaking output/tool correctness or causing swap.
   This target is a proposed acceptance criterion, not a promised result.

Stop if the existing snapshot cannot load correctly or warm continuation fails.
Investigate that concrete incompatibility before expanding models or adding a
custom agent framework. No production port, startup job, tailnet route, package
or client default was changed for this research. Windows remains deferred.
