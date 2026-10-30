chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk service_active 'systemctl is-active --quiet labweb'
chk enabled_for_boot 'systemctl is-enabled --quiet labweb'
chk runs_as_labweb '[ "$(ps -o user= -p $(systemctl show -p MainPID --value labweb) | tr -d " ")" = labweb ]'
chk answers 'curl -s -m 3 http://127.0.0.1:8080 | grep -q "hello from labweb"'
chk restart_policy 'case "$(systemctl show -p Restart --value labweb)" in on-failure|always|on-abnormal) true;; *) false;; esac'
