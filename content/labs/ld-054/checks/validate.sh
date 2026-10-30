chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk labweb_owns_port '[ "$(curl -s -m 3 http://127.0.0.1:8081 | tr -d "\n")" = "labweb v2" ]'
chk legacy_not_enabled 'st=$(systemctl is-enabled legacy.socket 2>&1); [ "$st" != enabled ]'
chk labweb_active 'systemctl is-active --quiet labweb'
