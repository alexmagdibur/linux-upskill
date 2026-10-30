for n in r far; do ip netns add $n; done
ip link add hv0 type veth peer name rv0
ip link set rv0 netns r
ip link add rv1 type veth peer name fv1
ip link set rv1 netns r
ip link set fv1 netns far
ip addr add 10.61.0.1/24 dev hv0; ip link set hv0 up
R="nsenter --net=/run/netns/r"; F="nsenter --net=/run/netns/far"
$R ip addr add 10.61.0.2/24 dev rv0; $R ip link set rv0 up
$R ip addr add 10.62.0.2/24 dev rv1; $R ip link set rv1 up; $R ip link set lo up
$F ip addr add 10.62.0.3/24 dev fv1; $F ip link set fv1 up; $F ip link set lo up
$R sysctl -qw net.ipv4.ip_forward=0
