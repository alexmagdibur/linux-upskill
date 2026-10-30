cat > ~/bin/batch.py <<'EOT'
import argparse, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

lock = threading.Lock()

def log(event, task):
    with lock:
        print(json.dumps({"event": event, "task": task, "ts": time.time()}), flush=True)

def run_task(name, seconds, out, timeout):
    log("start", name)
    try:
        subprocess.run(["sleep", str(seconds)], timeout=timeout, check=True)
    except subprocess.TimeoutExpired:
        log("timeout", name)
        return
    open(os.path.join(out, name + ".done"), "w").close()
    log("finish", name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-parallel", type=int, default=2)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("tasks")
    a = ap.parse_args()
    tasks = [l.split() for l in open(a.tasks) if l.strip()]
    if a.dry_run:
        for name, _ in tasks:
            log("plan", name)
        return
    os.makedirs(a.out, exist_ok=True)
    with ThreadPoolExecutor(max_workers=a.max_parallel) as pool:
        for name, sec in tasks:
            pool.submit(run_task, name, sec, a.out, a.timeout)

main()
EOT
