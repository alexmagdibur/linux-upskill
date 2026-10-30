sudo mkdir -p /etc/systemd/system/labscan.service.d
printf '[Service]\nNoNewPrivileges=yes\n' | sudo tee /etc/systemd/system/labscan.service.d/x.conf > /dev/null
