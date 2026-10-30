install -d /opt/lab /var/lib/lab
cat > /opt/lab/app.py <<'EOT'
import os, sys, time
if not os.path.exists("/run/labdata/ready"):
    print("labdata not ready", file=sys.stderr)
    sys.exit(1)
print("labapp started", flush=True)
while True:
    time.sleep(5)
EOT
cat > /etc/systemd/system/labdata.service <<'EOT'
[Unit]
Description=Lab data (готовится 4 секунды)

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'sleep 4; mkdir -p /run/labdata; touch /run/labdata/ready'

[Install]
WantedBy=multi-user.target
EOT
cat > /etc/systemd/system/labapp.service <<'EOT'
[Unit]
Description=Lab app

[Service]
ExecStart=/usr/bin/python3 /opt/lab/app.py

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable labdata.service labapp.service >/dev/null 2>&1
