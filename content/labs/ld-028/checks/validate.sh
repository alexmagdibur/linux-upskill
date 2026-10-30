chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
as() { runuser -u "$1" -- sh -c "$2"; }

chk user_ok 'u=$(getent passwd labsvc); [ -n "$u" ] && echo "$u" | grep -q ":/usr/sbin/nologin$" && [ "$(id -u labsvc)" -lt 1000 ] && [ ! -d "$(echo "$u" | cut -d: -f6)" ]'
chk reads_config 'as labsvc "cat /srv/labsvc/app.conf" | grep -q port=8080'
chk config_readonly '! as labsvc "echo x >> /srv/labsvc/app.conf" && ! as labsvc "rm -f /srv/labsvc/app.conf"'
chk writes_data 'as labsvc "touch /srv/labsvc/data/probe && rm /srv/labsvc/data/probe"'
chk secret_closed '! as labsvc "cat /srv/secret/key" && [ "$(stat -c %a /srv/secret)" != 777 ] && [ $(( 0$(stat -c %a /srv/secret/key) & 0007 )) -eq 0 ]'
