mkdir -p ~/data
python3 - <<'EOT'
import json, os
rows = []
for i in range(1, 101):
    rows.append({"endpoint": "/a", "ms": (i * 37) % 100 + 1})
    rows.append({"endpoint": "/b", "ms": (i * 53) % 100 + 1})
    rows.append({"endpoint": "/c", "ms": ((i * 7) % 100 + 1) * 2})
with open(os.path.expanduser("~/data/resp.jsonl"), "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
EOT
