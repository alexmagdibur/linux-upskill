install -d -o student -g student /home/student/ansible /home/student/ansible/templates
install -d /etc/labsvc2 /opt/lab
echo "port=8071" > /etc/labsvc2/app.conf
cat > /opt/lab/svc2.py <<'EOT'
import http.server, socketserver
port = int([l.split("=")[1] for l in open("/etc/labsvc2/app.conf") if l.startswith("port=")][0])
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
EOT
cat > /etc/systemd/system/labsvc2.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/svc2.py
WorkingDirectory=/opt/lab
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labsvc2 >/dev/null 2>&1
