chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk storage_persistent '[ -d /var/log/journal ] && systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -E "^Storage=" | tail -n 1 | grep -qx "Storage=persistent"'
chk size_limited 'v=$(systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -E "^SystemMaxUse=" | tail -n 1 | cut -d= -f2); [ -n "$v" ] && [ "$(numfmt --from=iec "${v%B}")" -le 104857600 ]'
chk survives_reboot 'journalctl -b -1 --no-pager 2>/dev/null | grep -q LABMARK-BEFORE-REBOOT'
