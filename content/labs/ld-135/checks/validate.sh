chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
analyze() { python3 - "$1" <<'EOT'
import json, os, sys
E = "/home/student/.ex"
def events(name):
    out = []
    for line in open(os.path.join(E, name)):
        out.append(json.loads(line))
    return out
what = sys.argv[1]
try:
    if what == "dry":
        ev = events("dry.log")
        ok = sum(1 for e in ev if e["event"] == "plan") == 6 and open(E + "/dry.n").read().strip() == "0"
    elif what == "parallel":
        ev = events("run.log")
        marks = sorted((e["ts"], 1 if e["event"] == "start" else -1) for e in ev if e["event"] in ("start", "finish"))
        cur = peak = 0
        for _, d in sorted(marks, key=lambda m: (m[0], m[1])):
            cur += d
            peak = max(peak, cur)
        files = open(E + "/run.files").read().split()
        ok = 1 <= peak <= 2 and files == ["t%d.done" % i for i in range(1, 7)] and peak == 2
    elif what == "timeout":
        ev = events("to.log")
        files = open(E + "/to.files").read().split()
        ok = any(e["event"] == "timeout" and e["task"] == "slow" for e in ev) and files == ["fast.done"]
    else:
        ev = events("run.log") + events("dry.log")
        ok = bool(ev) and all({"event", "task", "ts"} <= set(e) and isinstance(e["ts"], (int, float)) for e in ev)
except Exception:
    ok = False
print("OK" if ok else "BAD")
EOT
}
chk dry_run '[ "$(analyze dry)" = OK ]'
chk parallel_limit '[ "$(analyze parallel)" = OK ]'
chk timeout_kills '[ "$(analyze timeout)" = OK ]'
chk json_logs '[ "$(analyze logs)" = OK ]'
