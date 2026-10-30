chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
T=labbackup.timer
chk timer_active 'systemctl is-active --quiet $T && systemctl is-enabled --quiet $T'
chk persistent_random '[ "$(systemctl show -p Persistent --value $T)" = yes ] && [ "$(systemctl show -p RandomizedDelayUSec --value $T)" != 0 ]'
chk schedule_visible 'systemctl show -p TimersCalendar --value $T | grep -q "03:00" && [ -n "$(systemctl show -p NextElapseUSecRealtime --value $T)" ] && [ "$(systemd-analyze verify /etc/systemd/system/$T 2>&1 | grep -ci error)" = 0 ]'
