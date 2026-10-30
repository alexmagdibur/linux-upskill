chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
pid=$(systemctl show -p MainPID --value labcap)
eff=$(awk '/^CapEff/{print $2}' /proc/$pid/status)
chk capeff_minimal '[ "$(capsh --decode=$eff | sed "s/^0x[0-9a-f]*=//")" = cap_net_bind_service ]'
chk still_listening 'ss -ltn | grep -q "127.0.0.1:81 "'
