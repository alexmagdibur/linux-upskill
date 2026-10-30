chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cmp_json() { python3 - "$1" <<'EOT'
import json, sys
try:
    got = json.load(open("/home/student/.ex/%s.out" % sys.argv[1]))
except Exception:
    print("BAD"); raise SystemExit
if sys.argv[1] == "small":
    exp = {"alice": 10.5, "bob": 5.2, "юзер": 1.1}
else:
    exp = {}
    for i in range(600000):
        if i % 3:
            exp["u%d" % (i % 10)] = exp.get("u%d" % (i % 10), 0) + (i % 7) + 0.5
ok = set(got) == set(exp) and all(abs(float(got[k]) - exp[k]) < 0.011 for k in exp)
print("OK" if ok else "BAD")
EOT
}
chk small_cases '[ "$(cmp_json small)" = OK ]'
chk large_stream '[ "$(cmp_json large)" = OK ]'
