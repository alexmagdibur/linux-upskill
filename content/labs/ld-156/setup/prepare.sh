install -d /opt/lab /run/lab /var/lib/labapp
mkfifo /run/lab/jobs.fifo
chmod 666 /run/lab/jobs.fifo
cat > /opt/lab/hang.py <<'EOT'
with open("/run/lab/jobs.fifo") as f:   # блокируется до появления записывающей стороны
    data = f.read()
open("/var/lib/labapp/hang-done", "w").write("done\n")
import time
while True:
    time.sleep(60)
EOT
cat > /etc/systemd/system/labhang.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/hang.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labhang >/dev/null 2>&1
sleep 1
systemctl show -p MainPID --value labhang > /var/lib/lab-hang-pid
