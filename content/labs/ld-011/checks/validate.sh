chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk_csv() { python3 - <<'EOT'
import csv
try:
    rows = list(csv.reader(open("/home/student/errors.csv", newline="")))
except Exception:
    print("BAD"); raise SystemExit
exp = [["id", "message", "level", "host"], ["2", "disk full, retry later", "ERROR", "db1"], ["3", "plain failure", "ERROR", "web2"], ["5", "multi, comma, fields", "ERROR", "cache1"]]
print("OK" if rows == exp else "BAD")
EOT
}
chk errors '[ "$(chk_csv)" = OK ]'
