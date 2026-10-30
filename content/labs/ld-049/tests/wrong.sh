sudo tee /etc/systemd/system/labweb.service > /dev/null <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/web.py
EOT
sudo systemctl daemon-reload
sudo systemctl start labweb
