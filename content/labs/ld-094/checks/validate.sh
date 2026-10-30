chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk topology 'ip netns list | grep -qw app && ip netns list | grep -qw db && NS app ip -4 -br addr | grep -q "10.70.1.2/24" && NS db ip -4 -br addr | grep -q "10.70.2.2/24" && ip -4 -br addr | grep -q "10.70.1.1/24" && ip -4 -br addr | grep -q "10.70.2.1/24"'
chk forwarding '[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]'
chk app_to_db 'NS app ping -c1 -W2 10.70.2.2 && NS db ping -c1 -W2 10.70.1.2'
