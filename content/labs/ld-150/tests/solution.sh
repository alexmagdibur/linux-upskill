sudo mkdir -p /etc/systemd/system/labcap.service.d
printf '[Service]\nCapabilityBoundingSet=CAP_NET_BIND_SERVICE\nAmbientCapabilities=CAP_NET_BIND_SERVICE\n' | sudo tee /etc/systemd/system/labcap.service.d/caps.conf > /dev/null
