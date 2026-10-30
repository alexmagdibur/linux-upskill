chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
n1=$(sqlite3 /var/lib/labapp/orders.db "select count(*) from orders"); sleep 1; n2=$(sqlite3 /var/lib/labapp/orders.db "select count(*) from orders")
chk backup_valid '[ "$(sqlite3 /var/backups/labapp/orders.bak "PRAGMA integrity_check")" = ok ] && [ "$(sqlite3 /var/backups/labapp/orders.bak "select count(*) from orders")" -gt 0 ]'
chk restore_valid '[ "$(sqlite3 /var/lib/labapp/restored.db "PRAGMA integrity_check")" = ok ] && [ "$(sqlite3 /var/lib/labapp/restored.db "select count(*) from orders")" -gt 0 ]'
chk source_running 'systemctl is-active --quiet labdb-writer && [ "$n2" -gt "$n1" ]'
