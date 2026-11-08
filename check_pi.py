"""Require a streamed Pi read/edit cycle on a disposable Python fixture."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parent
fixture = Path(tempfile.mkdtemp(prefix='pi-fixture-', dir=root / '.runtime'))
source = 'def add(a, b):\n    return a - b\n'
expected = 'def add(a, b):\n    return a + b\n'
(fixture / 'calculator.py').write_text(source)
start = time.monotonic()
command = [sys.executable, str(root / 'pi.py'), '--print', '--mode', 'json',
           '--no-session', '--no-approve', '--tools', 'read,edit',
           '--system-prompt', 'You are a coding assistant. Use the provided tools to read and edit the requested file. Work only in the current directory. After editing, report what you changed.',
           'Read calculator.py, then use the edit tool to fix add(a, b) so it adds the two arguments. Preserve every other byte, including the trailing newline. Do not create any other files.']
result = subprocess.run(command, cwd=fixture, text=True, capture_output=True, timeout=300)
(root / '.runtime/pi-acceptance.jsonl').write_text(result.stdout)
(root / '.runtime/pi-acceptance.stderr').write_text(result.stderr)
assert result.returncode == 0, result.stderr[-2000:]
events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
started = [e.get('toolName') for e in events if e.get('type') == 'tool_execution_start']
ended = [e for e in events if e.get('type') == 'tool_execution_end']
assert 'read' in started and 'edit' in started, started
assert len(ended) >= 2 and not any(e.get('isError') for e in ended), ended
assert (fixture / 'calculator.py').read_text() == expected
assert sorted(f.name for f in fixture.iterdir()) == ['calculator.py']
# Check behavior separately, without granting the model shell execution.
subprocess.run([sys.executable, '-c', 'from calculator import add; assert add(19,23)==42; assert add(-2,3)==1; assert add(0,0)==0'], cwd=fixture, check=True)
summary = {'test': 'pi_read_edit', 'seconds': round(time.monotonic() - start, 3),
           'tools': started, 'tool_results': len(ended), 'exact_edit': True,
           'python_assertions': 3, 'client': '1.5.0'}
(root / '.runtime/pi-results.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
