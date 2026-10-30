printf '[Journal]\nStorage=persistent\nSystemMaxUse=50M\n' | sudo tee /etc/systemd/journald.conf.d/50-persistent.conf > /dev/null
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
