install -d /opt/lab /opt/labsite/releases/1 /opt/labsite/releases/2 /var/lib/lab
echo v1 > /opt/labsite/releases/1/value; echo v2 > /opt/labsite/releases/2/value
ln -s releases/1 /opt/labsite/current
cat > /opt/lab/site.py <<'EOT'
import http.server, signal, socketserver

def load():
    global value
    value = open("/opt/labsite/current/value").read().strip().encode() + b"\n"

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(value)))
        self.end_headers()
        self.wfile.write(value)
    def log_message(self, *a):
        pass

load()
signal.signal(signal.SIGHUP, lambda *_: load())
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8090), H).serve_forever()
EOT
cat > /etc/systemd/system/labsite.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/site.py
ExecReload=/bin/kill -HUP $MAINPID
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labsite.service >/dev/null 2>&1
sleep 1
systemctl show -p MainPID --value labsite > /var/lib/lab/pid0
