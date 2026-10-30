sudo sed -i '/^min-cache-ttl=/d' /etc/dnsmasq-cache.conf
sudo sed -i 's/^local-ttl=.*/local-ttl=30/' /etc/dnsmasq-auth.conf
sudo systemctl restart dnsmasq-auth dnsmasq-cache
sleep 1
