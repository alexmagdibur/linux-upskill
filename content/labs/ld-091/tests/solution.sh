sudo ip route add 10.62.0.0/24 via 10.61.0.2
sudo nsenter --net=/run/netns/r sysctl -w net.ipv4.ip_forward=1
sudo nsenter --net=/run/netns/far ip route add 10.61.0.0/24 via 10.62.0.2
