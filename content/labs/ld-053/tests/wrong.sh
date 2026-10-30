sudo tee /etc/systemd/system/labbackup.timer > /dev/null <<'EOT'
[Timer]
OnCalendar=*-*-* 03:00:00

[Install]
WantedBy=timers.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now labbackup.timer
