chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
prop() { systemctl show -p "$1" --value labscan; }
chk sandbox_props 'case "$(prop ProtectSystem)" in strict|full) true;; *) false;; esac && [ "$(prop ProtectHome)" != no ] && [ "$(prop PrivateTmp)" = yes ] && [ "$(prop NoNewPrivileges)" = yes ]'
chk effect_blocked 'grep -qx "etc=blocked home=blocked" /var/lib/labapp/probe.txt'
chk still_works 'systemctl is-active --quiet labscan && [ $(( $(date +%s) - $(cut -d. -f1 /var/lib/labapp/heartbeat) )) -le 5 ]'
