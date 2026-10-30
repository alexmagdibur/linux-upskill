sudo ip netns add labns
sudo ip link add vlab0 type veth peer name vlab1
sudo ip link set vlab1 netns labns
sudo ip addr add 10.77.0.1/24 dev vlab0
sudo ip link set vlab0 up
sudo nsenter --net=/run/netns/labns ip addr add 10.77.0.2/24 dev vlab1
sudo nsenter --net=/run/netns/labns ip link set vlab1 up
sudo nsenter --net=/run/netns/labns ip link set lo up
