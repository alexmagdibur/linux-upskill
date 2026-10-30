chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk flaky_recovers 'systemctl is-active --quiet flaky'
chk broken_visible 'systemctl is-failed --quiet broken && [ "$(systemctl show -p NRestarts --value broken)" -le 10 ]'
chk limits_explicit 'for u in flaky broken; do systemctl cat $u | grep -q "^StartLimitBurst=" && systemctl cat $u | grep -q "^StartLimitIntervalSec=" && [ "$(systemctl show -p StartLimitBurst --value $u)" -le 10 ] || exit 1; done'
