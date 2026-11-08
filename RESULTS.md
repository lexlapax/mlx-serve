# Pilot results, 2026-11-08

## Outcome

The local API and Pi coding-client pilot passed on Mac Studio. Pi read a Python
fixture, applied the exact requested edit, then read it back. All three tool
results succeeded. Three independent Python assertions passed. The fixture test
is a compatibility check, not an assessment of broad coding ability.

The plan was committed as d15d109 before installation. This record accompanies
the implementation commit. The repository is local-only, with no remote.

## Runtime

- Apple M1 Ultra, 48 GPU cores, 64 GiB unified RAM; macOS 26.7.3, build 25G416.
- Metal device discovery and a GPU matrix multiplication passed.
- vllm-mlx: 0.6.0.
- mlx: 0.32.4.
- mlx-lm: 0.31.3.
- mlx-vlm: 0.7.12.
- transformers: 5.22.2.
- python: 3.12.9.
- pi: 1.5.0.
- node: 26.13.0.
- Model: mlx-community/Qwen3.8-27B-4bit.
- Exact revision: `10c35caafbb80f7dc6a7a432cdd11af10a6d4818`.
- API: `http://127.0.0.1:8008/v1`, model `macstudio-local`, qwen3_xml parser.
- Single-user SimpleEngine, thinking disabled, deterministic sampling.
- Both Python and npm dependency trees locked; global Python/npm unchanged.

## Measurements

| Request | Input tokens | Output tokens | Wall seconds |
|---|---:|---:|---:|
| cold_chat | 28 | 3 | 2.712 |
| warm_chat | 28 | 3 | 0.443 |
| stream | 25 | 84 | 3.214 |
| tool_call | 281 | 16 | 2.585 |
| tool_result | 321 | 8 | 2.358 |
| after_cancel | 28 | 3 | 0.89 |
| long_prompt | 9023 | 2 | 56.326 |

The short streamed answer's first content token arrived in 0.349
seconds. Its 84 output tokens over 3.214
seconds give about 26 output tokens/second including prompt processing. These
are single-run observations, not a performance guarantee. Cold/warm refer to
requests after the model was already loaded; startup time is excluded.

Pi 1.5.0 completed the read/edit/read fixture in 28.013 seconds. Only
read/edit tools were allowed. The test runner executed Python assertions
separately; model-driven shell execution was not tested.

A 120-sample, one-second-interval observation during the test window recorded
peak resident memory of 15.634 GiB, minimum system-available memory
of 21.371 GiB, and zero swap use. Server-reported peak Metal
allocation was 16.91 GiB. RSS and Metal allocation are different
views of unified memory and must not be added together. These observations do
not establish full-context or concurrent-request memory limits.

## What passed

- Pinned model download and local loading without remote model code.
- Model listing, ordinary chat and streaming completion with final marker.
- Structured tool call, matching tool result and correct final response.
- Client disconnect during generation; the next request succeeded.
- A 9,023-token synthetic input returned the requested value correctly.
- Pi streamed tool execution, exact file edit and Python behavior checks.
- Final simplified launcher restarted; model listing and generation rechecked.
- Frozen dependency lock check, installed dependency consistency, Python syntax
  checks and Git whitespace checks passed.

## Practical limits and skipped checks

- The model's hybrid cache types disable system-prefix KV caching in this text
  route. Warm arithmetic timing does not demonstrate prefix reuse. Reprocessing
  a 9K-token prompt took about 56 seconds, which matters for longer agent turns.
- Pi's 16K context setting is a client budget, not an API input restriction.
  Full 16K/32K contexts, compaction and long autonomous sessions remain untested.
- Images, simultaneous clients, real repository tasks and model-driven shell
  execution were not tested. The selected model loads through MLX-VLM and
  routes text through MLX-LM; image capability is not claimed as verified.
- No login service, Tailscale exposure or existing Assistant/Herdr integration
  was applied. Startup after logout/reboot is deferred.
- MLX allocation/cache limits are process-local, not total resident-memory caps.
- The upstream published acceptance used a different snapshot and software
  stack; this report records the locally installed versions and actual tests.

## Next action

Operator: try Pi using README.md in a disposable or suitable project. After
acceptance, assistant can prepare login startup and private Tailscale deployment
in dotsetup. Push requires approval and a remote destination for mlx-serve.

Machine-readable evidence: [pilot-2026-11-08.json](results/pilot-2026-11-08.json).
Only synthetic test content is committed. Session/event logs remain ignored.
