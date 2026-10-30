cat > /etc/systemd/system/labburn.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 -c "while True: pass"
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labburn >/dev/null 2>&1
