sudo tee /usr/local/bin/lab-backup.sh > /dev/null <<'EOT'
#!/bin/bash
set -euo pipefail
D=/var/backups/labapp
ts=$(date +%Y%m%d-%H%M%S)
f=$D/labapp-$ts.tar.gz
tar -czf "$f" -C /var/lib/labapp data
tar -tzf "$f" > /dev/null
(cd "$D" && sha256sum "$(basename "$f")" > "$(basename "$f").sha256")
ls -1t $D/labapp-*.tar.gz | tail -n +4 | while read -r old; do rm -f "$old" "$old.sha256"; done
EOT
sudo chmod 755 /usr/local/bin/lab-backup.sh
sudo tee /etc/systemd/system/lab-backup.service > /dev/null <<'EOT'
[Service]
Type=oneshot
ExecStart=/usr/local/bin/lab-backup.sh
EOT
sudo tee /etc/systemd/system/lab-backup.timer > /dev/null <<'EOT'
[Timer]
OnCalendar=daily
Persistent=true
[Install]
WantedBy=timers.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now lab-backup.timer
