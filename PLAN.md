# MLX serving pilot on Mac Studio

## User outcome and scope

Run local Apple Silicon inference for coding agents such as Pi and for general
chat/document work from ~/projects/lexlapax/mlx-serve. Codex is optional.
Hardware: M1 Ultra, 64 GiB unified memory, 48 GPU cores; macOS 26.7.3.
The user approved committing this plan and proceeding with the local pilot on
2026-11-08, including an isolated Python installation and model download.

## Selected approach

Use native arm64 Python 3.12, uv, a project-local .venv and locked dependencies.
Pilot vllm-mlx with a single 4-bit model and Pi through Chat Completions.
Keep direct MLX-LM/MLX-VLM available as diagnostic baselines through the same
compatible dependency set. Do not implement another inference engine or proxy.

First candidate: mlx-community/Qwen3.8-27B-4bit with qwen3_xml tool parsing,
based on upstream's published Pi tool-call/file-edit acceptance. Pin a verified
model revision before download. That upstream test used different hardware and
macOS; it does not establish performance or compatibility on this Mac.
Fallback: a supported Qwen coding model if the first candidate cannot be loaded
or cannot complete the test. Record evidence for any change of model or server.

Start on 127.0.0.1:8008 if free, with one active generation, an initial context
budget of 16K tokens and bounded output. Evaluate 32K only after a passing pilot.
Aim to keep total server working memory below 40–44 GiB, leaving desktop room;
this is a planning target, not a verified hard memory cap. Do not raise macOS
wired-memory limits or enable large caches without evidence and review.

## Sequence and acceptance

1. Commit this plan before installation.
2. Verify registry/source versions, pin dependencies, create .venv and verify
   MLX sees the Metal GPU. Keep packages and model artifacts out of Git.
3. Download one pinned model; start the local API with its required parser.
4. Verify model listing, ordinary and streamed responses, cancellation, and
   a complete tool-call/result round trip.
5. Run Pi with isolated configuration and no inherited extensions against a
   disposable fixture. Require a correct file edit, a tool result and successful
   completion. Keep all existing Assistant/Herdr sessions and config unchanged.
6. Measure cold/warm response timing, generation throughput, memory and swap.
   Exercise a longer prompt and record actual context tested. Stop at a bounded,
   usable single-user pilot; do not expand indefinitely into benchmarking.
7. Commit reproducible scripts, locked dependencies, instructions and results.
   Record the host outcome in dotsetup. No push is authorized by this request.

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

- https://github.com/waybarrios/vllm-mlx
- https://github.com/waybarrios/vllm-mlx/blob/main/docs/guides/client-acceptance.md
- https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md
- https://github.com/Neywa-Labs/mlx-vlm
- https://github.com/jundot/omlx
- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md
- https://huggingface.co/mlx-community/Qwen3.8-27B-4bit

## Status

Pilot installed and verified on 2026-11-08. API and Pi acceptance passed;
see RESULTS.md for versions, measurements and untested behavior. Operator tries
the local client next. Login startup and private network access remain deferred.
