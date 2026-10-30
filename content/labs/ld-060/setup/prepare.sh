install -d /opt/lab /var/log/labapp
mount -t tmpfs -o size=4m,mode=755 tmpfs /var/log/labapp
echo "boot-record: important" > /var/log/labapp/app.log
dd if=/dev/zero of=/var/log/labapp/app.log.2023.old bs=1k count=3900 2>/dev/null
cat > /opt/lab/logger.py <<'EOT'
import time
while True:
    try:
        with open("/var/log/labapp/app.log", "a") as f:
            f.write("tick %d\n" % time.time())
    except OSError:
        pass
    time.sleep(0.5)
EOT
cat > /etc/systemd/system/labapp-log.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/logger.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labapp-log >/dev/null 2>&1
dd if=/dev/zero of=/var/log/labapp/filler bs=1k count=400 2>/dev/null || true
rm -f /var/log/labapp/filler
dd if=/dev/zero of=/var/log/labapp/.pad bs=1k count=100000 2>/dev/null || true
mv /var/log/labapp/.pad /var/log/labapp/app.log.2022.old
