"""Alternate isolated clients, recording synthetic fixture traffic and correctness."""
import argparse
import http.server
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from opencode_client import ROOT, BINARY, environment

SYSTEM = 'You are a coding assistant. Use the provided tools to read and edit the requested file. Work only in the current directory. After editing, report what you changed.'
PROMPT = 'Read calculator.py, then use the edit tool to fix add(a, b) so it adds the two arguments. Preserve every other byte, including the trailing newline. Read it back to verify the change. Do not create any other files.'
SOURCE = 'def add(a, b):\n    return a - b\n'
EXPECTED = 'def add(a, b):\n    return a + b\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8008')
    parser.add_argument('--label', default='vllm-mlx')
    parser.add_argument('--runs', type=int, default=3)
    args = parser.parse_args()
    runtime = ROOT / '.runtime' / f'comparison-{args.label}-{time.time_ns()}'
    runtime.mkdir(parents=True)
    requests = []

    class Proxy(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.send_error(404)
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            # Match effective sampling/output settings despite client adapter differences.
            payload.update(temperature=0, max_tokens=1024,
                           chat_template_kwargs={'enable_thinking': False})
            payload.pop('max_completion_tokens', None)
            if payload.get('stream'):
                payload['stream_options'] = {'include_usage': True}
            record = {'seconds': None, 'first_content_seconds': None, 'usage': None}
            requests.append(record)
            start = time.monotonic()
            try:
                req = urllib.request.Request(args.base_url + self.path,
                    data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=240) as response:
                    self.send_response(response.status)
                    self.send_header('Content-Type', response.headers.get('Content-Type', 'text/event-stream'))
                    self.end_headers()
                    for line in response:
                        if line.startswith(b'data: ') and line.strip() != b'data: [DONE]':
                            event = json.loads(line[6:])
                            if event.get('usage'):
                                record['usage'] = event['usage']
                            for choice in event.get('choices', []):
                                delta = choice.get('delta', {})
                                if (delta.get('content') or delta.get('tool_calls')) and record['first_content_seconds'] is None:
                                    record['first_content_seconds'] = round(time.monotonic()-start, 3)
                        self.wfile.write(line)
                        self.wfile.flush()
            except Exception as exc:
                record['error'] = str(exc)
            finally:
                record['seconds'] = round(time.monotonic()-start, 3)

    proxy = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{proxy.server_port}/v1'
    results = {'server': args.label, 'settings': {'temperature': 0, 'max_tokens': 1024,
        'thinking': False, 'normalization': 'loopback proxy enforces identical sampling and output cap'}, 'runs': []}
    for repeat in range(args.runs):
        for client in (['pi', 'opencode'] if repeat % 2 == 0 else ['opencode', 'pi']):
            directory = runtime / f'{repeat+1}-{client}'
            fixture = directory / 'fixture'
            fixture.mkdir(parents=True)
            (fixture / 'calculator.py').write_text(SOURCE)
            if client == 'pi':
                agent = directory / 'agent'
                agent.mkdir()
                provider = {'providers': {'macstudio': {'baseUrl': base, 'api': 'openai-completions',
                    'apiKey': 'local-no-auth', 'models': [{'id': 'macstudio-local', 'name': 'Local comparison',
                    'contextWindow': 16384, 'maxTokens': 1024, 'reasoning': False, 'input': ['text'],
                    'compat': {'supportsStore': False, 'supportsDeveloperRole': False,
                        'supportsReasoningEffort': False, 'maxTokensField': 'max_tokens'}}]}}}
                (agent / 'models.json').write_text(json.dumps(provider))
                env = os.environ.copy()
                env.update(PI_CODING_AGENT_DIR=str(agent), PI_OFFLINE='1', PI_TELEMETRY='0', PWD=str(fixture))
                command = ['/opt/homebrew/bin/node', str(ROOT / 'node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'),
                    '--model', 'macstudio/macstudio-local', '--thinking', 'off', '--no-extensions', '--no-mcp',
                    '--no-skills', '--no-prompt-templates', '--no-context-files', '--print', '--mode', 'json',
                    '--no-session', '--no-approve', '--tools', 'read,edit', '--system-prompt', SYSTEM, PROMPT]
            else:
                config = json.loads((ROOT / 'opencode.local.json').read_text())
                config['providers']['macstudio']['settings']['baseURL'] = base
                config['providers']['macstudio']['models']['macstudio-local']['limit']['output'] = 1024
                config['agents']['local']['system'] = SYSTEM
                config['permissions'] = [{'action': '*', 'resource': '*', 'effect': 'deny'},
                    {'action': 'read', 'resource': '*', 'effect': 'allow'},
                    {'action': 'edit', 'resource': '*calculator.py', 'effect': 'allow'}]
                env = environment(directory / 'client', config)
                env['PWD'] = str(fixture)
                command = [str(BINARY), 'run', '--standalone', '--format', 'json', '--title', 'Local comparison', PROMPT]
            first = len(requests)
            start = time.monotonic()
            process = subprocess.Popen(command, cwd=fixture, env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            timed_out = False
            try:
                stdout, stderr = process.communicate(timeout=300)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=15)
            elapsed = time.monotonic()-start
            (directory / 'events.jsonl').write_text(stdout)
            (directory / 'stderr.txt').write_text(stderr)
            events = [json.loads(line) for line in stdout.splitlines() if line.startswith('{')]
            if client == 'pi':
                tools = [e.get('toolName') for e in events if e.get('type') == 'tool_execution_start']
                tool_ok = not any(e.get('isError') for e in events if e.get('type') == 'tool_execution_end')
            else:
                parts = [e['part'] for e in events if e.get('type') == 'tool_use']
                tools = [p['tool'] for p in parts]
                tool_ok = all(p['state']['status'] == 'completed' for p in parts)
            exact = (fixture / 'calculator.py').read_text() == EXPECTED
            only_file = sorted(p.name for p in fixture.iterdir()) == ['calculator.py']
            assertions = False
            if exact:
                check = subprocess.run([sys.executable, '-B', '-c', 'from calculator import add; assert add(19,23)==42; assert add(-2,3)==1; assert add(0,0)==0'], cwd=fixture)
                assertions = check.returncode == 0
            row = {'client': client, 'repeat': repeat+1, 'seconds': round(elapsed, 3),
                'passed': process.returncode == 0 and not timed_out and exact and only_file and assertions and tool_ok and tools == ['read','edit','read'],
                'tools': tools, 'exact_edit': exact, 'python_assertions': 3 if assertions else 0,
                'requests': requests[first:]}
            results['runs'].append(row)
            output = ROOT / 'results' / f'clients-{args.label}-2026-11-08.json'
            output.write_text(json.dumps(results, indent=2)+'\n')
            print(json.dumps(row), flush=True)
    proxy.shutdown()
    if not all(r['passed'] for r in results['runs']):
        raise SystemExit('One or more fixture runs failed; see results')

if __name__ == '__main__':
    main()
