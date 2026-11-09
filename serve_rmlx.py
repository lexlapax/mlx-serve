"""Launch the pinned experimental Rust backend on its separate loopback port."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent
REVISION = '4c6e22ebc9ef4494189d2ffeb0ac1699ccd792f7'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dry-run', action='store_true')
parser.add_argument('--port', type=int, choices=(8008, 8009), default=8009,
                    help='8009 for isolated comparison; 8008 only after selecting this backend')
args = parser.parse_args()
source = ROOT / '.runtime/rmlx-source'
revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
if revision != REVISION:
    raise SystemExit('Rust source revision differs from the reviewed pilot pin')
model = json.loads((ROOT / 'model.json').read_text())
snapshot = Path((ROOT / '.runtime/model-path').read_text().strip())
if snapshot.name != model['revision'] or not (snapshot / 'config.json').is_file():
    raise SystemExit('Model snapshot does not match the pilot pin')
runtime = ROOT / '.runtime/rmlx'
registry = runtime / 'registry.json'
command = [str(source / 'target/release/rmlx'), 'serve', '--registry', str(registry),
    '--host', '127.0.0.1', '--port', str(args.port), '--max-ctx', '16384', '--max-tokens-cap', '2048',
    '--max-loaded-models', '1', '--max-queue-depth', '4', '--prompt-cache-slots', '4',
    '--prompt-cache-ram-gb', '2', '--kv-quant', 'none', '--default-temperature', '0',
    '--enable-thinking', 'false', '--idle-timeout-secs', '2h']
print('RMLX_PREFILL_CHUNK=512 RMLX_HOME='+shlex.quote(str(runtime))+' '+shlex.join(command), flush=True)
if not args.dry_run:
    runtime.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({'models':[{'id':model['served_name'],'path':str(snapshot)}]})+'\n')
    env = os.environ.copy()
    env.update(RMLX_HOME=str(runtime), RMLX_PREFILL_CHUNK='512')
    os.execve(command[0], command, env)
