sudo mkdir -p /etc/systemd/system/labscan.service.d
sudo tee /etc/systemd/system/labscan.service.d/sandbox.conf > /dev/null <<'EOT'
[Service]
ProtectSystem=strict
ReadWritePaths=/var/lib/labapp
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes
EOT
