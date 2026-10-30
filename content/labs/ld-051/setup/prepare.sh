install -d /opt/labapp/releases/1 /var/lib/labapp
cat > /opt/labapp/releases/1/run.py <<'EOT'
import time
while True:
    with open("/var/lib/labapp/hb", "w") as f:
        f.write(str(time.time()))
    time.sleep(1)
EOT
cat > /etc/systemd/system/labapp.service <<'EOT'
[Unit]
Description=Lab app

[Service]
WorkingDirectory=/opt/labapp/current
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labapp.service >/dev/null 2>&1 || true
sleep 3
