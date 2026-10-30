chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk bridge_ports '[ "$(ip -br link show master labbr0 2>/dev/null | awk "{print \$1}" | sed "s/@.*//" | sort | tr "\n" " ")" = "ha hb " ]'
chk ports_up 'ip -br link show labbr0 | grep -q "UP" && [ "$(cat /sys/class/net/ha/operstate)" = up ] && [ "$(cat /sys/class/net/hb/operstate)" = up ]'
chk a_pings_b 'NS a ping -c2 -W2 10.63.0.2'
