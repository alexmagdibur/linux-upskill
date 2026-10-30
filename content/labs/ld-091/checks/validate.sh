chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk end_to_end 'ping -c1 -W2 10.62.0.3'
chk forwarding_on '[ "$(NS r sysctl -n net.ipv4.ip_forward)" = 1 ]'
chk return_route 'NS far ip route get 10.61.0.1 | grep -q "via 10.62.0.2"'
