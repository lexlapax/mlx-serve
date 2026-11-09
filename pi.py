"""Open Pi against the local server with project-private configuration."""
import argparse
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parent
model = json.loads((root / "model.json").read_text())
parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
parser.add_argument("--backend", choices=("current", "rmlx"), default="current")
options, pi_args = parser.parse_known_args()
port = 8009 if options.backend == "rmlx" else 8008
agent = root / ".runtime" / ("pi-agent-rmlx" if options.backend == "rmlx" else "pi-agent")
agent.mkdir(parents=True, exist_ok=True)
provider = {"providers": {"macstudio": {
    "baseUrl": f"http://127.0.0.1:{port}/v1", "api": "openai-completions",
    "apiKey": "local-no-auth", "models": [{
        "id": model["served_name"], "name": "Mac Studio local MLX",
        "contextWindow": model["context_window"], "maxTokens": model["max_output_tokens"],
        "reasoning": False, "input": ["text"],
        "compat": {"supportsStore": False, "supportsDeveloperRole": False,
                   "supportsReasoningEffort": False, "maxTokensField": "max_tokens"},
        "samplingParams": {"temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
    }]}}}
(agent / "models.json").write_text(json.dumps(provider, indent=2) + "\n")
settings = agent / "settings.json"
if not settings.exists():
    settings.write_text(json.dumps({"compaction": {"enabled": True,
                        "reserveTokens": 2048, "keepRecentTokens": 4096},
                        "branchSummary": {"reserveTokens": 2048}}, indent=2) + "\n")
os.environ["PI_CODING_AGENT_DIR"] = str(agent)
os.environ["PI_OFFLINE"] = "1"
os.environ["PI_TELEMETRY"] = "0"
os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")
node = "/opt/homebrew/bin/node"
cli = str(root / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js")
command = [node, cli, "--model", "macstudio/" + model["served_name"],
           "--thinking", "off", "--no-extensions", "--no-mcp", "--no-skills",
           "--no-prompt-templates", "--no-context-files", *pi_args]
os.execv(node, command)
