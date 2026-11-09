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

In progress. Direct probes use identical synthetic prompts, temperature 0,
thinking off and the existing snapshot. Servers run sequentially. Long-context
cold/repeat/append measurements are single samples per condition, not statistical
medians. Short decode has three samples. Cache correctness and reported reuse
must both pass; fast incorrect output does not count as an improvement.

The Rust source pin is 4c6e22ebc9ef4494189d2ffeb0ac1699ccd792f7 (rMLX 0.4.5).
Native Homebrew dependencies under review are MLX 0.32.4 / mlx-c 0.8.0. Upstream's
older NAX benchmark pin does not apply to M1–M4; its C ABI guard still applies.
See [upstream MLX pair documentation](https://github.com/Pushkinist/rMLX/blob/4c6e22ebc9ef4494189d2ffeb0ac1699ccd792f7/docs/MLX_PAIR.md).

The prepared Rust launcher uses loopback port 8009, private RMLX_HOME, 16K
context, output ceiling 2048, four cache slots / 2 GiB, no SSD caching, no KV
quantization, one loaded model, bounded queue depth four and prefill chunk 512.
No login service or tailnet route is added. Python retains its separate venv and
port 8008. Stop and verify the active pilot process before starting the other;
never load both model servers for these measurements.
