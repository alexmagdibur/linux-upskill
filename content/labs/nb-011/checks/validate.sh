chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk report '[ "$(cat /home/student/report.txt)" = "$(printf "Report: begin\nupskill")" ]'
