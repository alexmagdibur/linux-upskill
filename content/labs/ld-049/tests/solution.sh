sudo useradd --system --no-create-home --shell /usr/sbin/nologin labweb
sudo tee /etc/systemd/system/labweb.service > /dev/null <<'EOT'
[Unit]
Description=Lab web
After=network.target

[Service]
User=labweb
ExecStart=/usr/bin/python3 /opt/lab/web.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now labweb
