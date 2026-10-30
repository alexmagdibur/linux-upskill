sudo nsenter --net=/run/netns/hc nc -z -w2 10.83.0.1 8080 || true
h=$(sudo nft -a list chain inet filter input | grep -E 'dport 8080.*drop' | grep -o 'handle [0-9]*' | awk '{print $2}')
sudo nft delete rule inet filter input handle $h
