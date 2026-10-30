install -d /opt/lab
cat > /opt/lab/hs.py <<'EOT'
import socket
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8099))
s.listen(5)
while True:
    c, _ = s.accept()
    c.sendall(b"hello\n")
    c.close()
EOT
cat > /etc/systemd/system/labhs.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/hs.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labhs >/dev/null 2>&1
