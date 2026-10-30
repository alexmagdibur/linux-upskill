chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk ordered_and_required 'systemctl show -p After --value labapp | grep -qw labdata.service && systemctl show -p Requires --value labapp | grep -qw labdata.service'
chk app_running 'systemctl is-active --quiet labapp'
chk clean_boot '[ "$(journalctl -b -u labapp --no-pager -o cat | grep -c "labdata not ready")" = 0 ] && [ "$(systemctl show -p NRestarts --value labapp)" = 0 ]'
