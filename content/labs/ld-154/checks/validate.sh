chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NOW=1700000000
gen() { python3 - "$@" <<'EOT'
import sys
kind = sys.argv[1]
now = 1700000000
rows = []
def add(n, status=200, lat=80, age=10):
    for i in range(n):
        rows.append((now - age - i % 100, status, lat))
if kind == "errors":
    add(90); add(10, 500)
elif kind == "latency":
    add(90); add(10, 200, 900)
elif kind == "quiet":
    add(98); add(2, 500)
elif kind == "window":
    add(100)
    add(50, 500, 80, 400)
elif kind == "few":
    add(5, 500)
for r in rows:
    print(*r)
EOT
}
run() { gen "$1" > /tmp/.log_$1; /usr/local/bin/lab-alert /tmp/.log_$1 $NOW | head -n 1; }
chk errors_alert 'run errors | grep -q "^ALERT"'
chk latency_alert 'run latency | grep -q "^ALERT"'
chk quiet_ok 'run quiet | grep -q "^OK"'
chk window_respected 'run window | grep -q "^OK"'
chk min_requests 'run few | grep -q "^OK insufficient-data"'
