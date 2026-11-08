"""Fetch only the pinned model snapshot; no remote Python code is executed."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parent
model = json.loads((root / "model.json").read_text())
path = snapshot_download(repo_id=model["repo_id"], revision=model["revision"],
                         token=False, max_workers=4)
(root / ".runtime").mkdir(exist_ok=True)
(root / ".runtime" / "model-path").write_text(path + "\n")
print(path)
