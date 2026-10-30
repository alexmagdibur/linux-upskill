sudo mkdir -p /etc/systemd/system/labapp.service.d
printf '[Unit]\nAfter=labdata.service\nRequires=labdata.service\n' | sudo tee /etc/systemd/system/labapp.service.d/order.conf > /dev/null
sudo systemctl daemon-reload
