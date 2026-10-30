chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
S=/home/student/secure
chk report_readable '[ "$(cat $S/report.txt)" = "Q3 results" ]'
chk key_closed '[ "$(stat -c %a $S/key.pem)" = 600 ] && [ ! -r $S/key.pem ]'
