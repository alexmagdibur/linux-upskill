sudo tee /etc/systemd/system/labbackup.timer > /dev/null <<'EOT'
[Unit]
Description=Daily lab backup

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now labbackup.timer
