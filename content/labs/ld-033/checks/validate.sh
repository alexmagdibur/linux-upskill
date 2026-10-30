chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
want=$(pgrep -f 'svc.py 9102' | head -n 1)
chk right_pid '[ -n "$want" ] && [ "$(tr -d "[:space:]" < /home/student/pid.txt)" = "$want" ]'
chk all_alive 'pgrep -f "svc.py 9101" && pgrep -f "svc.py 9102" && pgrep -f "svc.py 9103"'
