ip netns add peer
ip link add hv0 type veth peer name hv1
ip link set hv1 netns peer
ip addr add 10.50.1.1/24 dev hv0; ip link set hv0 up
nsenter --net=/run/netns/peer ip addr add 10.50.1.2/24 dev hv1
nsenter --net=/run/netns/peer ip link set hv1 up
nsenter --net=/run/netns/peer ip link set lo up
ip route add 10.50.9.0/24 via 10.50.1.2
