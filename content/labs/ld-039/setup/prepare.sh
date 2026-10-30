install -d /opt/lab
cat > /opt/lab/leaky.py <<'EOT'
import time
fds = []
while True:
    fds.append(open("/dev/null"))   # дескриптор никогда не закрывается
    time.sleep(0.05)
EOT
cat > /etc/systemd/system/leaky.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/leaky.py
LimitNOFILE=128
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now leaky.service >/dev/null 2>&1
sleep 2
