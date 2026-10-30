python3 - <<'EOT'
import json, math
data = {}
for line in open("/home/student/data/resp.jsonl"):
    r = json.loads(line)
    data.setdefault(r["endpoint"], []).append(r["ms"])
out = {ep: sorted(v)[math.ceil(0.95 * len(v)) - 1] for ep, v in data.items()}
json.dump(out, open("/home/student/p95.json", "w"))
EOT
