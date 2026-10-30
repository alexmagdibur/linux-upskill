echo 'host-record=web.lab.test,10.20.0.10' | sudo tee /etc/dnsmasq.d/10-lab.conf > /dev/null
sudo systemctl restart dnsmasq
