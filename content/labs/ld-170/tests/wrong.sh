sudo tee /usr/local/bin/lab-backup.sh > /dev/null <<'EOT'
#!/bin/bash
tar -czf /var/backups/labapp/labapp-$(date +%s).tar.gz /var/lib/labapp/data
EOT
sudo chmod 755 /usr/local/bin/lab-backup.sh
sudo tee /etc/systemd/system/lab-backup.service > /dev/null <<'EOT'
[Service]
Type=oneshot
ExecStart=/usr/local/bin/lab-backup.sh
EOT
sudo systemctl daemon-reload
