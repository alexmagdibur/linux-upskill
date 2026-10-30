chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk_p95() { python3 - <<'EOT'
import json, math
try:
    got = json.load(open("/home/student/p95.json"))
except Exception:
    print("BAD"); raise SystemExit
data = {}
for line in open("/home/student/data/resp.jsonl"):
    r = json.loads(line)
    data.setdefault(r["endpoint"], []).append(r["ms"])
ok = set(got) == set(data)
for ep, vals in data.items():
    vals.sort()
    exp = vals[math.ceil(0.95 * len(vals)) - 1]
    if ep in got and abs(float(got[ep]) - exp) > max(1.0, 0.01 * exp):
        ok = False
print("OK" if ok else "BAD")
EOT
}
chk p95 '[ "$(chk_p95)" = OK ]'
