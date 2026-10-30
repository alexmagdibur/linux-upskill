chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS="nsenter --net=/run/netns/labns"
chk ns_exists 'ip netns list | grep -qw labns'
chk veth_pair 'ip -br addr show vlab0 | grep -q "10.77.0.1/24" && $NS ip -br addr show vlab1 | grep -q "10.77.0.2/24" && ip -br link show vlab0 | grep -q UP && $NS ip -br link show vlab1 | grep -q UP'
chk ping_both 'ping -c1 -W2 10.77.0.2 && $NS ping -c1 -W2 10.77.0.1'
