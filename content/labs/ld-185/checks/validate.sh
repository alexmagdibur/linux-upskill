chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk serves_v2 '[ "$(curl -s -m 3 http://127.0.0.1:8090 | tr -d "\n")" = v2 ]'
chk symlink_ok '[ "$(readlink -f /opt/labsite/current)" = /opt/labsite/releases/2 ]'
chk no_restart '[ "$(systemctl show -p MainPID --value labsite)" = "$(cat /var/lib/lab/pid0)" ] && [ "$(systemctl show -p NRestarts --value labsite)" = 0 ]'
