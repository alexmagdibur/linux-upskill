cat > ~/bin/parse.py <<'EOT'
import json, sys

rows = [json.loads(l) for l in sys.stdin]
totals = {}
for r in rows:
    if r.get("status") == "ok":
        totals[r["user"]] = totals.get(r["user"], 0.0) + float(r["amount"])
print(json.dumps(totals))
EOT
