sudo tee /etc/dnsmasq.d/10-lab.conf > /dev/null <<'EOT'
host-record=web.lab.test,10.20.0.10,fd00::10
cname=www.lab.test,web.lab.test
address=/blocked.lab.test/
EOT
sudo systemctl restart dnsmasq
sleep 1
