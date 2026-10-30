cat > /etc/systemd/system/labslow.service <<'EOT'
[Unit]
Description=Slow lab initialisation
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'sleep 15; touch /run/labslow.done'
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable labslow >/dev/null 2>&1
