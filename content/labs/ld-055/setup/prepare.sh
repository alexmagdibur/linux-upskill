install -d /opt/lab /var/lib/labapp
cat > /opt/lab/scan.py <<'EOT'
import os, time

def try_write(path):
    try:
        with open(path, "w") as f:
            f.write("x")
        os.remove(path)
        return "open"
    except OSError:
        return "blocked"

def try_home():
    try:
        os.listdir("/home/student")
        return "open"
    except OSError:
        return "blocked"

while True:
    with open("/var/lib/labapp/probe.txt", "w") as f:
        f.write("etc=%s home=%s\n" % (try_write("/etc/lab-probe"), try_home()))
    with open("/var/lib/labapp/heartbeat", "w") as f:
        f.write(str(time.time()))
    time.sleep(1)
EOT
cat > /etc/systemd/system/labscan.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/scan.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labscan >/dev/null 2>&1
sleep 2
