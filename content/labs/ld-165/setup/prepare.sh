install -d /opt/lab /var/lib/lab /etc/lab
cat > /opt/lab/secapp.py <<'EOT'
import os, time
ok = os.environ.get("DB_PASSWORD") == "S3cr3tPass"
with open("/var/lib/lab/auth.log", "a") as f:
    f.write("auth ok\n" if ok else "auth failed\n")
while True:
    time.sleep(5)
EOT
cat > /etc/systemd/system/labsecret.service <<'EOT'
[Service]
Environment=DB_PASSWORD=S3cr3tPass
ExecStart=/usr/bin/python3 /opt/lab/secapp.py --user=db --password=S3cr3tPass
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labsecret.service >/dev/null 2>&1
