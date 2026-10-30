printf '[Journal]\nSystemMaxUse=50M\n' | sudo tee /etc/systemd/journald.conf.d/50-limit.conf > /dev/null
sudo systemctl restart systemd-journald
