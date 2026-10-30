python3 - <<'EOT'
import json
data = {}
for line in open("/home/student/data/resp.jsonl"):
    r = json.loads(line)
    data.setdefault(r["endpoint"], []).append(r["ms"])
json.dump({ep: max(v) for ep, v in data.items()}, open("/home/student/p95.json", "w"))
EOT
