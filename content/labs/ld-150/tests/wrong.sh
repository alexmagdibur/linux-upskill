sudo mkdir -p /etc/systemd/system/labcap.service.d
printf '[Service]\nCapabilityBoundingSet=~CAP_SYS_ADMIN\n' | sudo tee /etc/systemd/system/labcap.service.d/caps.conf > /dev/null
