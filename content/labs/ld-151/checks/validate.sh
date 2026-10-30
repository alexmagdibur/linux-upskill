chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk filter_set 'systemctl show -p SystemCallFilter --value labseccomp | grep -q . && case "$(systemctl show -p SystemCallErrorNumber --value labseccomp)" in EPERM|1) true;; *) false;; esac'
chk mount_blocked 'grep -qx "mount=blocked" /var/lib/labapp/seccomp.txt'
chk alive 'systemctl is-active --quiet labseccomp && [ $(( $(date +%s) - $(cut -d. -f1 /var/lib/labapp/heartbeat2) )) -le 5 ]'
