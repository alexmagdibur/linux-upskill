sudo tee /etc/systemd/system/labslow.service > /dev/null <<'EOT'
[Unit]
Description=Slow lab initialisation
[Service]
Type=exec
ExecStart=/bin/sh -c 'sleep 15; touch /run/labslow.done'
[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
