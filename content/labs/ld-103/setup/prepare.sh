install -d /opt/lab
cat > /opt/lab/kabackend.py <<'EOT'
import http.server, socketserver, threading

count = 0
lock = threading.Lock()

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def setup(self):
        global count
        with lock:
            if not self.path_is_count:
                pass
        super().setup()
    path_is_count = False
    def do_GET(self):
        body = (str(count) + "\n").encode() if self.path == "/count" else b"hello\n"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass

class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    def process_request(self, request, client_address):
        global count
        # /count запрашивается напрямую с адреса 127.0.0.1 тем же сервером, поэтому считаем только соединения от nginx (порты не различаем):
        with lock:
            count += 1
        super().process_request(request, client_address)

S(("127.0.0.1", 9200), H).serve_forever()
EOT
cat > /etc/systemd/system/lab-kabackend.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/kabackend.py
[Install]
WantedBy=multi-user.target
EOT
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/ka.conf <<'EOT'
server {
    listen 127.0.0.1:8095;
    location / { proxy_pass http://127.0.0.1:9200; }
}
EOT
systemctl daemon-reload
systemctl enable --now lab-kabackend nginx >/dev/null 2>&1
sleep 1
