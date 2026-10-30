chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
D=/var/backups/labapp
newest=$(ls -1t $D/labapp-*.tar.gz 2>/dev/null | head -n 1)
chk rotation_ok '[ "$(ls $D/labapp-*.tar.gz 2>/dev/null | wc -l)" = 3 ] && [ "$(ls $D/labapp-*.sha256 2>/dev/null | wc -l)" -ge 1 ]'
chk archive_valid '[ -n "$newest" ] && tar -tzf "$newest" > /tmp/.list 2>/dev/null && grep -q users.db /tmp/.list && grep -q settings.conf /tmp/.list && grep -q "uploads/" /tmp/.list'
chk timer_enabled 'systemctl is-enabled --quiet lab-backup.timer && systemctl cat lab-backup.timer | grep -q "^OnCalendar="'
