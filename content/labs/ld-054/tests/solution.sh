sudo systemctl disable --now legacy.socket
sudo systemctl disable legacy.service 2>/dev/null || true
sudo systemctl restart labweb
