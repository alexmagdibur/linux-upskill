ip netns add srv
ip link add hv0 type veth peer name sv0
ip link set sv0 netns srv
ip addr add 10.64.0.1/24 dev hv0; ip link set hv0 up
nsenter --net=/run/netns/srv ip addr add 10.64.0.2/24 dev sv0
nsenter --net=/run/netns/srv ip link set sv0 mtu 1300
nsenter --net=/run/netns/srv ip link set sv0 up
