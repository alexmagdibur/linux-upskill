for pair in "app a 1" "db d 2"; do set -- $pair
  n=$1; p=$2; k=$3
  sudo ip netns add $n
  sudo ip link add h${p}1 type veth peer name ${p}0
  sudo ip link set ${p}0 netns $n
  sudo ip addr add 10.70.$k.1/24 dev h${p}1; sudo ip link set h${p}1 up
  sudo nsenter --net=/run/netns/$n ip addr add 10.70.$k.2/24 dev ${p}0
  sudo nsenter --net=/run/netns/$n ip link set ${p}0 up
  sudo nsenter --net=/run/netns/$n ip link set lo up
  sudo nsenter --net=/run/netns/$n ip route add default via 10.70.$k.1
done
sudo sysctl -w net.ipv4.ip_forward=1
