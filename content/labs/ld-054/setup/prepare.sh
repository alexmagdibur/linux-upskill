install -d /opt/lab
cat > /opt/lab/server.py <<'EOT'
import os, socket, sys
name, ver = sys.argv[1], sys.argv[2]
if os.environ.get("LISTEN_FDS") == "1":
    s = socket.socket(fileno=3)            # сокет передал systemd (socket activation)
else:
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 8081))
    s.listen(5)
while True:
    c, _ = s.accept()
    c.recv(1024)
    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (len(name + " " + ver) + 1, (name + " " + ver + "\n").encode()))
    c.close()
EOT
cat > /etc/systemd/system/legacy.socket <<'EOT'
[Socket]
ListenStream=127.0.0.1:8081

[Install]
WantedBy=sockets.target
EOT
cat > /etc/systemd/system/legacy.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/server.py legacy v1
EOT
cat > /etc/systemd/system/labweb.service <<'EOT'
[Unit]
Description=Lab web v2

[Service]
ExecStart=/usr/bin/python3 /opt/lab/server.py labweb v2
Restart=no

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now legacy.socket >/dev/null 2>&1
systemctl enable labweb.service >/dev/null 2>&1
systemctl start labweb.service >/dev/null 2>&1 || true
