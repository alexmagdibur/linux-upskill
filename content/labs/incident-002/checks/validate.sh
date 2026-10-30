chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk log_writable 'tail -n 1 /var/log/app/app.log | grep -q "service ok"'
chk current_log_kept 'grep -q "MARKER current-log-keep-me" /var/log/app/app.log'
chk space_freed '[ "$(df -k --output=avail /var/log/app | tail -n 1 | tr -d " ")" -gt 2048 ]'
