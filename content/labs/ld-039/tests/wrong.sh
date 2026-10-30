sudo mkdir -p /etc/systemd/system/leaky.service.d
printf '[Service]\nLimitNOFILE=1000000\n' | sudo tee /etc/systemd/system/leaky.service.d/limit.conf > /dev/null
sudo systemctl daemon-reload
sudo systemctl restart leaky
sleep 4
