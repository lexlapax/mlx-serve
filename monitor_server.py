"""Sample one known model process during a bounded comparison."""
import argparse
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('pid', type=int)
parser.add_argument('label')
parser.add_argument('--seconds', type=int, default=1200)
args = parser.parse_args()
peak = 0
samples = 0
swap = set()
output = Path(__file__).resolve().parent / 'results' / f'memory-{args.label}-2026-11-08.json'
for _ in range(args.seconds):
    rss = subprocess.run(['ps', '-o', 'rss=', '-p', str(args.pid)], text=True, capture_output=True)
    if rss.returncode or not rss.stdout.strip():
        break
    peak = max(peak, int(rss.stdout.strip()))
    samples += 1
    value = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'vm.swapusage'], text=True).strip()
    swap.add(value)
    output.write_text(json.dumps({'samples': samples, 'peak_rss_gib': round(peak/1024**2, 3), 'swap_observations': sorted(swap)}, indent=2)+'\n')
    time.sleep(1)
