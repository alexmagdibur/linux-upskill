chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk big_ping 'ping -M do -s 1400 -c2 -W2 10.64.0.2'
chk mtu_equal '[ "$(cat /sys/class/net/hv0/mtu)" = "$(NS srv ip -o link show sv0 | grep -o "mtu [0-9]*" | cut -d" " -f2)" ]'
