cat > ~/bin/parse.py <<'EOT'
import json, sys

totals = {}
for line in sys.stdin:
    try:
        rec = json.loads(line)
        if rec.get("status") != "ok":
            continue
        user, amount = rec["user"], float(rec["amount"])
    except (ValueError, KeyError, TypeError, AttributeError):
        print("skip: %r" % line[:40], file=sys.stderr)
        continue
    totals[user] = totals.get(user, 0.0) + amount
print(json.dumps({k: round(v, 2) for k, v in totals.items()}, ensure_ascii=False))
EOT
