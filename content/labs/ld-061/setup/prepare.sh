install -d /opt/lab /var/log/lab
cat > /opt/lab/logger.py <<'EOT'
import signal, time

PATH = "/var/log/lab/app.log"
f = open(PATH, "a", buffering=1)
n = 0

def reopen(*_):
    global f
    f.close()
    f = open(PATH, "a", buffering=1)

signal.signal(signal.SIGHUP, reopen)
while True:
    n += 1
    f.write("line %d\n" % n)
    time.sleep(0.05)
EOT
cat > /etc/systemd/system/lablogger.service <<'EOT'
[Unit]
Description=Lab logger

[Service]
ExecStart=/usr/bin/python3 /opt/lab/logger.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now lablogger.service >/dev/null 2>&1
sleep 2
