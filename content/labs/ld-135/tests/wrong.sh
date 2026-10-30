cat > ~/bin/batch.py <<'EOT'
import argparse, json, os, subprocess, threading, time

def log(event, task):
    print(json.dumps({"event": event, "task": task, "ts": time.time()}), flush=True)

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--max-parallel", type=int, default=2)
ap.add_argument("--timeout", type=float, default=None)
ap.add_argument("--out", required=True)
ap.add_argument("tasks")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
ths = []
for l in open(a.tasks):
    name, sec = l.split()
    def w(n=name, s=sec):
        log("start", n)
        subprocess.run(["sleep", s])
        open(os.path.join(a.out, n + ".done"), "w").close()
        log("finish", n)
    t = threading.Thread(target=w); t.start(); ths.append(t)
for t in ths:
    t.join()
EOT
