sudo sed -i 's/8081 127.0.0.1/8081 10.65.0.1/' /etc/systemd/system/labweb.service
sudo systemctl daemon-reload
sudo systemctl restart labweb
sleep 1
