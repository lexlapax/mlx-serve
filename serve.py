"""Run the single-user pilot in the foreground, bound to loopback."""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()
model = json.loads((root / "model.json").read_text())
marker = root / ".runtime" / "model-path"
if not marker.exists():
    raise SystemExit("Run uv run --frozen python download.py first")
snapshot = Path(marker.read_text().strip())
if snapshot.name != model["revision"] or not (snapshot / "config.json").is_file():
    raise SystemExit("Model path does not match the pinned snapshot")
command = [str(root / ".venv/bin/vllm-mlx"), "serve", str(snapshot),
           "--served-model-name", model["served_name"],
           "--host", "127.0.0.1", "--port", "8008",
           "--enable-auto-tool-choice", "--tool-call-parser", model["tool_parser"],
           "--default-chat-template-kwargs", '{"enable_thinking": false}',
           "--default-temperature", "0", "--max-tokens", "1024",
           "--max-request-tokens", str(model["max_output_tokens"]),
           "--prefill-step-size", "512", "--enable-metrics", "--offline"]
print(shlex.join(command), flush=True)
if not args.dry_run:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    import mlx.core as mx
    from vllm_mlx.cli import main

    # SimpleEngine does not apply the batching-only GPU utilization flag.
    mx.set_memory_limit(40 * 1024**3)
    mx.set_cache_limit(512 * 1024**2)
    sys.argv = command
    main()
