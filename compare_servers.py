"""Direct synthetic SSE, cache-continuation, tools, cancellation and queue probes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8008')
parser.add_argument('--label', default='vllm-mlx')
args = parser.parse_args()
rows = []
output = ROOT / 'results' / f'server-{args.label}-2026-11-08.json'


def request(messages, **extra):
    body = dict(model='macstudio-local', messages=messages, max_tokens=128,
        temperature=0, chat_template_kwargs={'enable_thinking': False}, stream=True,
        stream_options={'include_usage': True})
    body.update(extra)
    req = urllib.request.Request(args.base_url+'/v1/chat/completions',
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=240)


def cache():
    try:
        with urllib.request.urlopen(args.base_url+'/metrics/cache', timeout=5) as response:
            data = json.load(response)
            return {key: data[key] for key in ('models', 'tokens_in', 'tokens_out', 'error_counts') if key in data}
    except (urllib.error.URLError, ValueError):
        return None


def chat(label, messages, cancel=False, **extra):
    before = cache()
    start = time.monotonic()
    first = last = None
    text = ''
    usage = None
    calls = {}
    done = False
    error = None
    try:
        with request(messages, **extra) as response:
            for line in response:
                if time.monotonic() - start > 240:
                    raise TimeoutError('Request exceeded the 240-second wall-clock limit')
                if not line.startswith(b'data: '):
                    continue
                raw = line[6:].strip()
                if raw == b'[DONE]':
                    done = True
                    break
                event = json.loads(raw)
                if event.get('error'):
                    error = event['error']
                    break
                if event.get('usage'):
                    usage = event['usage']
                for choice in event.get('choices', []):
                    delta = choice.get('delta', {})
                    content = delta.get('content') or ''
                    if content or delta.get('tool_calls'):
                        now = time.monotonic()
                        if first is None:
                            first = now
                        last = now
                    text += content
                    for call in delta.get('tool_calls') or []:
                        target = calls.setdefault(call.get('index', 0), {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                        if call.get('id'):
                            target['id'] = call['id']
                        for key in ('name', 'arguments'):
                            target['function'][key] += call.get('function', {}).get(key) or ''
                if cancel and first:
                    break
    except urllib.error.HTTPError as exc:
        error = {'http_status': exc.code, 'body': exc.read().decode()[:1000]}
    except Exception as exc:
        error = str(exc)
    elapsed = time.monotonic()-start
    tokens = usage.get('completion_tokens') if usage else None
    row = {'test': label, 'seconds': round(elapsed, 3),
        'first_content_seconds': round(first-start, 3) if first else None,
        'estimated_decode_tokens_per_second': round((tokens-1)/(last-first), 2) if tokens and last and first and last > first else None,
        'usage': usage, 'text': text, 'tool_calls': list(calls.values()),
        'stream_done': done, 'cancelled_by_test': cancel, 'error': error,
        'cache_before': before, 'cache_after': cache()}
    return row


def save(row):
    rows.append(row)
    output.write_text(json.dumps({'server': args.label, 'runs': rows}, indent=2)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k not in ('text','cache_before','cache_after','tool_calls')}), flush=True)


def user(text):
    return {'role': 'user', 'content': text}

for index in range(3):
    save(chat(f'short_{index+1}', [user('Explain how hash tables handle collisions in several detailed paragraphs.')]))
for length, count in [('5k', 450), ('9k', 820)]:
    prompt = f'Reference archive {length}:\n'+''.join(f'item {i}: alpha beta gamma delta\n' for i in range(count))
    prompt += '\nThe deployment marker is amber-8426. Reply with only the deployment marker.'
    messages = [user(prompt)]
    for state in ('cold', 'repeat'):
        row = chat(f'{length}_{state}', messages, max_tokens=32)
        row['correct'] = 'amber-8426' in row['text']
        save(row)
    messages += [{'role':'assistant','content':row['text']}, user('What were the four digits in that marker? Reply with only the digits.')]
    row = chat(f'{length}_append', messages, max_tokens=32)
    row['correct'] = '8426' in row['text']
    save(row)
    if not row['correct']:
        raise SystemExit('Stop: continuation correctness failed')

tools = [{'type': 'function', 'function': {'name': 'read_pilot_marker',
    'description': 'Read the current pilot marker.', 'parameters': {'type':'object','properties':{},'required':[]}}}]
messages = [user('Call read_pilot_marker, then reply with the exact marker it returns. Do not guess the marker.')]
row = chat('tool_call', messages, tools=tools, tool_choice='auto')
row['correct'] = len(row['tool_calls']) == 1 and row['tool_calls'][0]['function']['name'] == 'read_pilot_marker' and json.loads(row['tool_calls'][0]['function']['arguments']) == {}
save(row)
if row['correct']:
    invocation = row['tool_calls'][0]
    messages += [{'role':'assistant', 'content':row['text'] or None, 'tool_calls':row['tool_calls']},
        {'role':'tool','tool_call_id':invocation['id'],'content':'violet-7391'}]
    row = chat('tool_result', messages, tools=tools)
    row['correct'] = 'violet-7391' in row['text']
    save(row)
save(chat('cancel', [user('Count upwards from 1 to 500.')], cancel=True, max_tokens=1024))
time.sleep(2)
row = chat('after_cancel', [user('What is 19 + 23? Reply only with the number.')], max_tokens=16)
row['correct'] = row['text'].strip() == '42'
save(row)
with ThreadPoolExecutor(max_workers=2) as pool:
    first = pool.submit(chat, 'overlap_first', [user('Explain how binary search works in detail.')])
    time.sleep(0.2)
    second = pool.submit(chat, 'overlap_second', [user('What is 19 + 23? Reply only with the number.')], max_tokens=16)
    save(first.result())
    row = second.result()
    row['correct'] = row['text'].strip() == '42'
    save(row)
print('Finished; inspect correctness, errors and cache evidence before selecting a backend.', flush=True)
