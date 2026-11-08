"""Verify private OpenCode restart/resume, compaction and permission decisions."""
import json
import socket
import secrets
import base64
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from opencode_client import BINARY, ROOT, environment

context = json.loads((ROOT / '.runtime/opencode-test-context.json').read_text())
fixture = Path(context['fixture'])
runtime = Path(context['runtime'])
rows = [json.loads(line) for line in (ROOT / '.runtime/opencode-acceptance.jsonl').read_text().splitlines() if line.startswith('{')]
session_id = rows[0]['sessionID']
config = json.loads((ROOT / 'opencode.local.json').read_text())
# Force a useful compaction in a short synthetic session; production keeps 4096.
config['compaction']['keep']['tokens'] = 256
env = environment(runtime, config)
env["OPENCODE_SERVER_PASSWORD"] = secrets.token_urlsafe(32)
authorization = "Basic " + base64.b64encode(("opencode:" + env["OPENCODE_SERVER_PASSWORD"]).encode()).decode()
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
log = (ROOT / '.runtime/opencode-session-server.log').open('w')
server = None
results = {}


def api(path, data=None, method=None):
    req = urllib.request.Request(base + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type': 'application/json', 'Authorization': authorization}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'{exc.code} {path}: {exc.read().decode()[:1000]}') from exc


def start():
    process = subprocess.Popen([str(BINARY), 'serve', '--hostname', '127.0.0.1', '--port', str(port)],
                               cwd=fixture, env=env, stdout=log, stderr=log)
    last_error = None
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('Test server exited; inspect private log')
        try:
            api('/api/info')
            return process
        except (OSError, RuntimeError) as exc:
            last_error = str(exc)
            time.sleep(0.1)
    process.terminate()
    process.wait(timeout=10)
    raise RuntimeError(f'Test server did not become ready: {last_error}')


def run(label, prompt):
    start_time = time.monotonic()
    output = subprocess.run([str(BINARY), 'run', '--server', base, '--session', session_id,
                             '--format', 'json', prompt], cwd=fixture, env=env,
                            capture_output=True, text=True, timeout=180)
    (ROOT / f'.runtime/opencode-{label}.jsonl').write_text(output.stdout)
    (ROOT / f'.runtime/opencode-{label}.stderr').write_text(output.stderr)
    assert output.returncode == 0, output.stderr[-2000:]
    events = [json.loads(line) for line in output.stdout.splitlines() if line.startswith('{')]
    assert not any(e.get('type') == 'error' for e in events), events[-2:]
    text = ''.join(e['part'].get('text', '') for e in events if e.get('type') == 'text')
    results[label] = {'seconds': round(time.monotonic() - start_time, 3), 'text': text}
    print(label, json.dumps(results[label]), flush=True)
    return text


try:
    server = start()
    existing = api('/api/session/' + session_id)['data']
    assert existing['id'] == session_id
    assert 'cobalt-8426' in run('remember', 'Remember the marker cobalt-8426 for this session. Reply with only the marker. Do not use tools.')
    server.terminate()
    server.wait(timeout=15)
    server = start()
    assert 'cobalt-8426' in run('resume', 'What marker did I ask you to remember? Reply with only the marker. Do not use tools.')
    before = api(f'/api/session/{session_id}/message')
    (ROOT / '.runtime/opencode-before-compact.json').write_text(json.dumps(before, indent=2))
    compact = api(f'/api/session/{session_id}/compact', {})
    print('compact accepted', json.dumps(compact), flush=True)
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        state = api(f'/api/session/{session_id}')['data']
        messages = api(f'/api/session/{session_id}/message')
        (ROOT / '.runtime/opencode-after-compact.json').write_text(json.dumps(messages, indent=2))
        data = messages.get('data', [])
        completed = [m for m in data if m.get('type') == 'compaction' and m.get('status') == 'completed']
        if completed:
            results['compaction'] = {'completed': True}
            break
        time.sleep(1)
    else:
        print('compaction state', json.dumps(state), flush=True)
        raise RuntimeError('Compaction completion not observed; inspect captured messages')
    assert 'cobalt-8426' in run('after_compaction', 'What is the exact marker I asked you to remember? Reply with only the marker. Do not use tools.')
    (ROOT / '.runtime/opencode-session-results.json').write_text(json.dumps(results, indent=2) + '\n')
finally:
    if server is not None and server.poll() is None:
        server.terminate()
        server.wait(timeout=15)
    log.close()
