install -d /opt/lab
cat > /opt/lab/cap.py <<'EOT'
import socket, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 81))
s.listen(5)
while True:
    time.sleep(60)
EOT
cat > /etc/systemd/system/labcap.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/cap.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labcap >/dev/null 2>&1
sleep 1
