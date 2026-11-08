"""Exercise the local API and save timings from synthetic prompts only."""
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
MODEL = json.loads((ROOT / 'model.json').read_text())['served_name']
BASE = 'http://127.0.0.1:8008'
results = []


def request(messages, **extra):
    body = dict(model=MODEL, messages=messages, max_tokens=128, temperature=0)
    body.update(extra)
    req = urllib.request.Request(BASE + '/v1/chat/completions',
                                 data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=300)


def chat(label, messages, **extra):
    start = time.monotonic()
    with request(messages, **extra) as response:
        data = json.load(response)
    row = {'test': label, 'seconds': round(time.monotonic() - start, 3),
           'usage': data.get('usage'), 'message': data['choices'][0]['message']}
    results.append(row)
    print(json.dumps(row), flush=True)
    return data['choices'][0]['message']


with urllib.request.urlopen(BASE + '/v1/models', timeout=10) as response:
    assert MODEL in [m['id'] for m in json.load(response)['data']]
messages = [{'role': 'user', 'content': 'What is 19 + 23? Answer with only the number.'}]
for label in ('cold_chat', 'warm_chat'):
    assert '42' in chat(label, messages).get('content', '')

start = time.monotonic()
first = None
text = ''
usage = None
finished = False
with request([{'role': 'user', 'content': 'Explain in three sentences why a Python virtual environment is useful.'}],
             stream=True, stream_options={'include_usage': True}) as response:
    for line in response:
        if not line.startswith(b'data: '):
            continue
        raw = line[6:].strip()
        if raw == b'[DONE]':
            finished = True
            break
        event = json.loads(raw)
        if event.get('usage'):
            usage = event['usage']
        for choice in event.get('choices', []):
            content = choice.get('delta', {}).get('content') or ''
            if content and first is None:
                first = time.monotonic() - start
            text += content
assert finished and text and first is not None
row = {'test': 'stream', 'ttft_seconds': round(first, 3),
       'seconds': round(time.monotonic() - start, 3), 'usage': usage, 'text': text}
results.append(row)
print(json.dumps(row), flush=True)

tools = [{'type': 'function', 'function': {
    'name': 'read_pilot_marker', 'description': 'Read the current pilot marker.',
    'parameters': {'type': 'object', 'properties': {}, 'required': []}}}]
messages = [{'role': 'user', 'content': 'Call read_pilot_marker, then reply with the exact marker it returns. Do not guess the marker.'}]
call = chat('tool_call', messages, tools=tools, tool_choice='auto')
assert len(call.get('tool_calls', [])) == 1, call
invocation = call['tool_calls'][0]
assert invocation['function']['name'] == 'read_pilot_marker'
assert json.loads(invocation['function']['arguments']) == {}
messages += [call, {'role': 'tool', 'tool_call_id': invocation['id'], 'content': 'violet-7391'}]
assert 'violet-7391' in chat('tool_result', messages, tools=tools).get('content', '')

# Disconnect after the first generated token, then require the next request to work.
with request([{'role': 'user', 'content': 'Count upwards from 1 to 500.'}], stream=True, max_tokens=1024) as response:
    for line in response:
        if line.startswith(b'data: ') and line[6:].strip() != b'[DONE]':
            event = json.loads(line[6:])
            if any(c.get('delta', {}).get('content') for c in event.get('choices', [])):
                break
# Give the generation worker a bounded opportunity to observe disconnection.
time.sleep(2)
assert '42' in chat('after_cancel', [{'role': 'user', 'content': 'What is 19 + 23? Reply only with the number.'}]).get('content', '')

context = '\n'.join(f'Record {i}: the archive contains ordinary sample data.' for i in range(650))
long_prompt = context + '\nFinal record: the deployment color is amber. What is the deployment color? Reply with only the color.'
assert 'amber' in chat('long_prompt', [{'role': 'user', 'content': long_prompt}], max_tokens=32).get('content', '').lower()
(ROOT / '.runtime' / 'api-results.json').write_text(json.dumps(results, indent=2) + '\n')
print('PASS: models, chat, streaming, tool round trip, cancellation recovery, long prompt')
