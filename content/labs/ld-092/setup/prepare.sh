for n in a b; do ip netns add $n; ip link add h$n type veth peer name ${n}0; ip link set ${n}0 netns $n; done
nsenter --net=/run/netns/a ip addr add 10.63.0.1/24 dev a0; nsenter --net=/run/netns/a ip link set a0 up
nsenter --net=/run/netns/b ip addr add 10.63.0.2/24 dev b0; nsenter --net=/run/netns/b ip link set b0 up
