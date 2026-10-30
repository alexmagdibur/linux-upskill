chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk_py() { python3 - "$1" <<'EOT'
import json, os, sys
try:
    d = json.load(open("/home/student/answer.json"))
except Exception:
    print("BAD"); sys.exit()
if sys.argv[1] == "valid":
    print("OK" if isinstance(d, dict) and {"cwd", "home", "bash"} <= set(d) else "BAD")
else:
    ok = d.get("cwd") == "/home/student/maze/a/b" and d.get("home") == "/home/student" and d.get("bash") in ("/usr/bin/bash", "/bin/bash")
    print("OK" if ok else "BAD")
EOT
}
chk json_valid '[ "$(chk_py valid)" = OK ]'
chk paths_ok '[ "$(chk_py paths)" = OK ]'
