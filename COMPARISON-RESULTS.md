# Client and server comparison — 2026-11-08

Machine: M1 Ultra Mac Studio, 48 GPU cores, 64 GiB, macOS 26.7.3.
Model: mlx-community/Qwen3.8-27B-4bit, revision
10c35caafbb80f7dc6a7a432cdd11af10a6d4818. Its declared architecture is
Qwen3_5ForConditionalGeneration. No new model was downloaded.

## Client comparison on vllm-mlx

| Client | Runs (seconds) | Median | Correct runs |
|---|---|---|---|
| Pi 1.5.0 | 29.689, 29.000, 29.036 | 29.036 | 3/3 |
| OpenCode 2.2.6 | 47.147, 47.127, 47.245 | 47.147 | 3/3 |

Pi took 38.4% less elapsed time on this fixture. Both made four model calls and
performed read/edit/read. Pi's per-call input counts were 821, 875, 965, 1019;
OpenCode's were 1532, 1601, 1684, 1753. First-content waits were roughly 5.4–6.3
seconds for Pi and 9.6–10.8 for OpenCode. Most elapsed time was in model requests,
consistent with prompt-processing overhead rather than terminal rendering.

Method: alternating order Pi/OpenCode, OpenCode/Pi, Pi/OpenCode; fresh isolated
client state and fixture each time; identical system and user instructions;
read/edit permissions only; exact edited bytes, no extra files and three
independent Python assertions. A loopback measurement proxy enforced temperature
0, thinking off, output cap 1024 and streamed usage on the wire. Client-specific
tool schemas and message wrappers remain part of the comparison. The production
endpoint and existing client configs were not changed. Tool/first-text timing
starts at each proxied inference request; elapsed task time includes client startup.

This is a tiny deterministic edit, not a representative coding-quality benchmark.
The results justify a Pi usability trial, not a claim that Pi solves the backend
cache problem. See [raw measurements](results/clients-vllm-mlx-2026-11-08.json).
Reproduce with `python3 compare_clients.py` while only vllm-mlx is serving.
Private events and client state stay in ignored `.runtime/`.

## Server comparison

The existing server passed long-context answers,
streamed tool calls/results and cancellation recovery. It rejected the second
overlapping request with a streamed InternalServerError (code 500), consistent
with its serialized busy behavior. Direct short-prompt decode measured
28.91–28.96 tokens/s. First-content latency was 30.207/30.178/30.346 seconds
for 5K cold/repeat/append and 56.517/131.658/56.175 seconds for 9K. The 9K
repeat is a confounded outlier: dependency fetching occurred during part of it,
so do not attribute the excess to the server alone. The adjacent 9K continuation
was correct and returned to roughly 56 seconds.

Direct probes use identical synthetic prompts, temperature 0,
thinking off and the existing snapshot. Servers run sequentially. Long-context
cold/repeat/append measurements are single samples per condition, not statistical
medians. Short decode has three samples. Cache correctness and reported reuse
must both pass; fast incorrect output does not count as an improvement.

The Rust source pin is 4c6e22ebc9ef4494189d2ffeb0ac1699ccd792f7 (rMLX 0.4.5).
Installed native Homebrew dependencies are MLX 0.32.4 / mlx-c 0.8.0. Upstream's
older NAX benchmark pin does not apply to M1–M4; its C ABI guard still applies.
See [upstream MLX pair documentation](https://github.com/Pushkinist/rMLX/blob/4c6e22ebc9ef4494189d2ffeb0ac1699ccd792f7/docs/MLX_PAIR.md).

The prepared Rust launcher uses loopback port 8009, private RMLX_HOME, 16K
context, output ceiling 2048, four cache slots / 2 GiB, no SSD caching, no KV
quantization, one loaded model, bounded queue depth four and prefill chunk 512.
No login service or tailnet route is added. Python retains its separate venv and
port 8008. Stop and verify the active pilot process before starting the other;
never load both model servers for these measurements.


## Reproduce the isolated Rust build

The host recipe records `mlx-c`; Homebrew installs `mlx` as its dependency.
The reviewed host package dry run also listed unrelated Allbert, so deployment
used a targeted `brew install mlx-c` instead of applying that unrelated package.
No global Python packages or system Python files were changed.

From this repository, after reviewing the native dependency versions:

```sh
HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 brew install mlx-c
git clone https://github.com/Pushkinist/rMLX.git .runtime/rmlx-source
git -C .runtime/rmlx-source checkout --detach 4c6e22ebc9ef4494189d2ffeb0ac1699ccd792f7
(cd .runtime/rmlx-source && cargo build --release --locked --bin rmlx)
python3 serve_rmlx.py --dry-run
```

Stop only the verified Python pilot process before `python3 serve_rmlx.py`.
In another terminal run:

```sh
python3 compare_servers.py --base-url http://127.0.0.1:8009 --label rmlx
python3 compare_clients.py --base-url http://127.0.0.1:8009 --label rmlx
```

Rollback: stop the verified `rmlx serve` pilot, then start
`uv run --frozen python serve.py` and check `http://127.0.0.1:8008/v1/models`.
This returns the existing client endpoint without editing any client settings.


## Rust API results

The exact model loaded successfully. All direct correctness probes passed,
including changed follow-up questions, streamed tool call/result, disconnect
recovery and two overlapping requests. The second overlapping request waited
about five seconds for the first generation, then answered correctly; the old
server emitted an internal-error stream instead.

| Measurement | vllm-mlx 0.6.0 | rMLX 0.4.5 |
|---|---:|---:|
| Short response decode, three samples | 28.91–28.96 tok/s | 27.62–27.71 tok/s |
| 4,877-token cold first content | 30.207 s | 30.492 s |
| Same 4,877-token prompt repeated | 30.178 s | 0.006 s |
| Follow-up growing to 4,912 tokens | 30.346 s | 0.634 s |
| 8,947-token cold first content | 56.517 s | 55.782 s |
| Same 8,947-token prompt repeated | 131.658 s (confounded outlier) | 0.018 s |
| Follow-up growing to 8,982 tokens | 56.175 s | 0.776 s |

The changed follow-ups are the useful result: about 48× and 72× shorter waits
in these single samples. Exact repeated prompts can use cached first-token
state and should not be mistaken for new generation throughput. Short decode
was about 4% slower in Rust; cold prefill was essentially unchanged. The gain
comes from preserving context, not from Rust making the matrix operations faster.

Cache metrics increased on repeat/append. The Rust server's prefill log explicitly
reported 4,877 reused + 35 forwarded tokens and 8,947 reused + 35 forwarded tokens
for the changed follow-ups. Correct marker/digit answers verified continuation.
The active cache budget stayed bounded; the test used no SSD cache or speculative
model. These are single-user results with a four-deep queue, not continuous batching.

See [Rust measurements](results/server-rmlx-2026-11-08.json) and
[Python baseline](results/server-vllm-mlx-2026-11-08.json).
Combined coding-client trials passed; see below.


## Combined coding clients and recommendation

All six initial rMLX coding runs passed, followed by all six model-reload runs:
read/edit/read, exact file bytes, no extra files and three independent assertions.
The initial Rust run times were Pi 14.363/13.956/13.997 seconds and OpenCode
18.836/10.811/18.788 seconds. On the existing Python backend, their medians were
29.036 and 47.147 seconds respectively. The first combined Pi run took about
70% less time than the original OpenCode/Python median on this small fixture.

The model-reload trial produced Pi 13.954/13.950/13.702 seconds and OpenCode
18.745/10.725/18.442 seconds. **Reload is not a complete cache reset.** The
Qwen architecture cache is process-global; the server log proves that the second
OpenCode task reused 1280 prefix tokens even after unload/load. These are mixed
warm-cache task measurements, not six independent cold-process measurements.
The initial request of the first Pi and first OpenCode tasks reused zero tokens;
subsequent tool turns reused the earlier prompt as intended. Do not use the fast
10.7-second OpenCode sample as a cold baseline. A strict cold-process study would
restart the server between tasks; it is not needed to establish the cache gain
already verified by the direct changed-context probes.

Client-generated fixture paths also cause small input-count differences across
series (Pi roughly 818–821 initial tokens; OpenCode 1529–1532). Direct server
probes use exactly matching prompts and token counts. Client model/tool calls are
not byte-identical across products, which is part of their practical overhead.

**Recommendation:** use rMLX for this model's repeated coding turns, and try Pi
as the smaller client. Keep OpenCode installed: it also benefits substantially
from the new backend. Pi Durable is not needed for this terminal pilot. Preserve
edit/shell approval controls for real work. This tiny fixture does not establish
broad coding quality, long-session stability or interactive UI acceptance.

The explicit `python3 pi.py --backend rmlx` launcher is tested independently and
uses a separate private agent directory. Existing Pi configuration still points
to port 8008. Candidate activation on that existing endpoint uses the prepared
`python3 serve_rmlx.py --port 8008`; it must replace, not overlap, the old model
process. Permanent login startup and Tailscale exposure remain deferred.

Raw series: [initial combined runs](results/clients-rmlx-2026-11-08.json),
[model-reload runs](results/clients-rmlx-reload-2026-11-08.json).


## Memory and verification limits

600 one-second samples of the Python pilot peaked at 15.595 GiB process RSS;
551 Rust samples peaked at 15.029 GiB. Both reported zero swap throughout.
Rust's reported peak Metal allocation reached about 18.4 GiB during the coding
trials. RSS and Metal allocation are distinct views of unified memory, not values
to add together. The samples include idle/build or reload intervals as well as
requests; they are not a controlled memory-efficiency ranking.

The Rust release build passed against the installed C API. All eighteen coding
fixture runs passed. Both direct API suites passed semantic/tool/cancellation
checks; the expected comparison failure was the Python overlapping request.
The Rust overlap succeeded. Python syntax and Git whitespace checks passed.
No full upstream Rust suite, long-duration stress test, broad coding-quality
benchmark or operator interactive UI acceptance was performed.

Rollback is verified: the Rust pilot was stopped, Python was restored on
127.0.0.1:8008, model discovery passed and a chat request returned exactly 42.
Port 8009 has no listener. The active-backend selection remains pending operator
choice; no migration is inferred from the pilot approval. No automatic startup
or private-network route was added.
