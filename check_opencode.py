"""Check an isolated OpenCode read/edit cycle against the local model."""
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from opencode_client import BINARY, ROOT, environment

fixture = Path(tempfile.mkdtemp(prefix='opencode-fixture-', dir=ROOT / '.runtime'))
source = 'def add(a, b):\n    return a - b\n'
expected = 'def add(a, b):\n    return a + b\n'
(fixture / 'calculator.py').write_text(source)
config = json.loads((ROOT / 'opencode.local.json').read_text())
config['permissions'] = [
    {'action': '*', 'resource': '*', 'effect': 'deny'},
    {'action': 'read', 'resource': '*', 'effect': 'allow'},
    {'action': 'edit', 'resource': '*calculator.py', 'effect': 'allow'},
]
runtime = ROOT / '.runtime' / (fixture.name + '-client')
env = environment(runtime, config)
command = [str(BINARY), 'run', '--standalone', '--format', 'json', '--title', 'MLX fixture acceptance',
           'Read calculator.py, then use the edit tool to fix add(a, b) so it adds the two arguments. Preserve every other byte, including the trailing newline. Read it back to verify the change. Do not create any other files.']
start = time.monotonic()
process = subprocess.Popen(command, cwd=fixture, env=env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           start_new_session=True)
try:
    stdout, stderr = process.communicate(timeout=180)
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=15)
    (ROOT / '.runtime/opencode-timeout.stdout').write_text(stdout)
    (ROOT / '.runtime/opencode-timeout.stderr').write_text(stderr)
    raise
result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
(ROOT / '.runtime/opencode-acceptance.jsonl').write_text(result.stdout)
(ROOT / '.runtime/opencode-acceptance.stderr').write_text(result.stderr)
assert result.returncode == 0, result.stderr[-3000:]
events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
(ROOT / '.runtime/opencode-test-context.json').write_text(json.dumps({'fixture':str(fixture),'runtime':str(runtime)},indent=2)+'\n')
tool_events = [e['part'] for e in events if e.get('type') == 'tool_use']
assert [e['tool'] for e in tool_events] == ['read', 'edit', 'read']
assert all(e['state']['status'] == 'completed' for e in tool_events)
assert (fixture / 'calculator.py').read_text() == expected, result.stdout[-5000:]
assert sorted(f.name for f in fixture.iterdir()) == ['calculator.py']
subprocess.run([sys.executable, '-c', 'from calculator import add; assert add(19,23)==42; assert add(-2,3)==1; assert add(0,0)==0'], cwd=fixture, check=True)
summary = {'seconds': round(time.monotonic()-start,3), 'exact_edit': True,
           'python_assertions': 3, 'tools': [e['tool'] for e in tool_events],
           'tool_results_completed': True, 'version': '2.2.6',
           'steps': [e['part']['tokens'] for e in events if e.get('type') == 'step_finish']}
(ROOT / '.runtime/opencode-results.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
