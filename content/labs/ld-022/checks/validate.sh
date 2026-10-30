chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk space_freed '[ "$(df -k --output=avail /home/student | tail -n 1 | tr -d " ")" -gt 40960 ]'
chk service_alive 'pgrep -f "spool/holder.py" && [ -f /home/student/spool/app.log ]'
