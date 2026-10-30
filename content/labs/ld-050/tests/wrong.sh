sudo mkdir -p /etc/systemd/system/labapp.service.d
printf '[Service]\nRestart=always\nRestartSec=5\n' | sudo tee /etc/systemd/system/labapp.service.d/retry.conf > /dev/null
sudo systemctl daemon-reload
