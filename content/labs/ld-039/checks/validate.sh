chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
sleep 2
pid=$(systemctl show -p MainPID --value leaky); a=$(ls /proc/$pid/fd 2>/dev/null | wc -l); sleep 3
pid2=$(systemctl show -p MainPID --value leaky); b=$(ls /proc/$pid2/fd 2>/dev/null | wc -l)
chk service_running 'systemctl is-active --quiet leaky && [ "$pid" = "$pid2" ]'
chk fd_stable '[ "$pid" = "$pid2" ] && [ "$b" -le $((a + 5)) ]'
chk limit_kept '[ "$(systemctl show -p LimitNOFILE --value leaky)" -le 4096 ]'
chk clean_journal '[ "$(journalctl -u leaky --since "-6 seconds" --no-pager -o cat | grep -ci "too many open files")" = 0 ]'
