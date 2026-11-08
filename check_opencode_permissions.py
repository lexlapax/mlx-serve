"""Check that local OpenCode waits for and obeys fixture permission replies."""
import base64
import json
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from opencode_client import BINARY, ROOT, environment

fixture = Path(tempfile.mkdtemp(prefix='opencode-permissions-', dir=ROOT / '.runtime'))
runtime = ROOT / '.runtime' / (fixture.name + '-client')
config = json.loads((ROOT / 'opencode.local.json').read_text())
config['agents']['local']['steps'] = 3
env = environment(runtime, config)
env['OPENCODE_SERVER_PASSWORD'] = secrets.token_urlsafe(32)
auth = 'Basic ' + base64.b64encode(('opencode:' + env['OPENCODE_SERVER_PASSWORD']).encode()).decode()
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
base = f'http://127.0.0.1:{port}'
results = []


def api(path, data=None):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type':'application/json', 'Authorization':auth})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def eventually(check, seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.25)
    raise RuntimeError('Timed out waiting for the expected permission/session state')


def messages(sid):
    return api(f'/api/session/{sid}/message')['data']


def pending(sid):
    query = urllib.parse.urlencode({'location[directory]':str(fixture)})
    return next((r for r in api('/api/permission/request?' + query)['data'] if r['sessionID'] == sid), None)


def trial(label, action, decision, prompt, marker, expected):
    sid = api('/api/session', {'title':label, 'agent':'local',
              'model':{'providerID':'macstudio','id':'macstudio-local'},
              'location':{'directory':str(fixture)}})['data']['id']
    api(f'/api/session/{sid}/prompt', {'text':prompt})
    try:
        permission = eventually(lambda: pending(sid))
    except Exception:
        (ROOT / '.runtime/opencode-permission-failure.json').write_text(json.dumps(messages(sid), indent=2))
        raise
    assert permission['action'] == action, permission
    if action == 'edit':
        assert marker.read_text() == 'original\n'
    else:
        assert not marker.exists()
    api(f"/api/session/{sid}/permission/{permission['id']}/reply", {'decision':decision})
    def finished():
        for message in messages(sid):
            if message['type'] != 'assistant':
                continue
            for part in message['content']:
                if part['type'] != 'tool' or part['name'] != action:
                    continue
                state = part['state']
                if state['status'] in ('completed', 'error'):
                    return state
        return None
    done = eventually(finished)
    tools = [part for m in messages(sid) if m['type']=='assistant'
             for part in m['content'] if part['type']=='tool']
    if decision == 'reject':
        assert marker.read_text() == 'original\n'
        assert any(p['state']['status']=='error' for p in tools), tools
    else:
        assert marker.exists()
        if action == 'edit':
            assert marker.read_text() == expected
        assert any(p['state']['status']=='completed' for p in tools), tools
    assert done['status'] == ('error' if decision == 'reject' else 'completed'), done
    if decision == 'reject':
        assert 'declined' in done['error']['message'].lower(), done
    row = {'test':label,'action':action,'decision':decision,'waited_for_approval':True,
           'outcome_verified':True, 'tool_outcome':done['status']}
    results.append(row)
    print(json.dumps(row),flush=True)


with (ROOT / '.runtime/opencode-permission-server.log').open('w') as log:
    server = subprocess.Popen([str(BINARY),'serve','--hostname','127.0.0.1','--port',str(port)],
                              cwd=fixture,env=env,stdout=log,stderr=log)
    try:
        def ready():
            try:
                return api('/api/info')
            except OSError:
                return None
        eventually(ready,15)
        marker = fixture / 'approval.txt'
        marker.write_text('original\n')
        prompt = 'Read approval.txt and use edit to replace original with approved, preserving the final newline. If permission is rejected, stop and report it; do not retry.'
        trial('reject_edit','edit','reject',prompt,marker,None)
        trial('approve_edit','edit','once',prompt,marker,'approved\n')
        shell_marker = fixture / 'shell-marker.txt'
        trial('approve_shell','shell','once','Use the shell tool to run exactly /usr/bin/touch shell-marker.txt in the current directory, then stop.',shell_marker,None)
        (ROOT / '.runtime/opencode-permission-results.json').write_text(json.dumps(results,indent=2)+'\n')
    finally:
        server.terminate()
        server.wait(timeout=15)
