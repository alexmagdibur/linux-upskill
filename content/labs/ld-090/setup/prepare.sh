ip netns add gw
ip link add hv0 type veth peer name gv0
ip link set gv0 netns gw
nsenter --net=/run/netns/gw ip addr add 10.60.0.1/24 dev gv0
nsenter --net=/run/netns/gw ip link set gv0 up
nsenter --net=/run/netns/gw ip link set lo up
ip addr add 10.60.1.5/24 dev hv0
ip link set hv0 up
