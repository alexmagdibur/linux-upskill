chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
n1=$(systemctl show -p NRestarts --value labapp); sleep 3; n2=$(systemctl show -p NRestarts --value labapp)
t1=$(stat -c %Y /var/lib/labapp/hb 2>/dev/null || echo 0); sleep 2; t2=$(stat -c %Y /var/lib/labapp/hb 2>/dev/null || echo 0)
chk service_stable 'systemctl is-active --quiet labapp && [ "$n1" = "$n2" ]'
chk workdir_valid '[ -d "$(systemctl show -p WorkingDirectory --value labapp)" ]'
chk heartbeat_alive '[ "$t2" -gt "$t1" ]'
chk clean_journal '[ "$(journalctl -u labapp --since "-6 seconds" --no-pager -o cat | grep -c CHDIR)" = 0 ]'
