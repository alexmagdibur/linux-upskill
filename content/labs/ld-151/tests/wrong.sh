sudo mkdir -p /etc/systemd/system/labseccomp.service.d
printf '[Service]\nNoNewPrivileges=yes\n' | sudo tee /etc/systemd/system/labseccomp.service.d/x.conf > /dev/null
