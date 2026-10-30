install -d /opt/lab /var/log/lab /var/lib/lab/queue
cat > /opt/lab/traceapp.py <<'EOT'
import http.server, os, socketserver, time

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rid = self.headers.get("X-Request-ID", "-")
        with open("/var/log/lab/app.log", "a") as f:
            f.write("rid=%s path=%s\n" % (rid, self.path))
        with open("/var/lib/lab/queue/%d.job" % (time.time() * 1000), "w") as f:
            f.write(rid)
        self.send_response(200); self.send_header("Content-Length", "3"); self.end_headers(); self.wfile.write(b"ok\n")
    def log_message(self, *a):
        pass

socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 9100), H).serve_forever()
EOT
cat > /opt/lab/traceworker.py <<'EOT'
import glob, os, time
while True:
    for p in sorted(glob.glob("/var/lib/lab/queue/*.job")):
        rid = open(p).read().strip()
        with open("/var/log/lab/worker.log", "a") as f:
            f.write("rid=%s processed\n" % rid)
        os.remove(p)
    time.sleep(0.3)
EOT
for u in app worker; do
cat > /etc/systemd/system/lab-trace$u.service <<EOT
[Service]
ExecStart=/usr/bin/python3 /opt/lab/trace$u.py
[Install]
WantedBy=multi-user.target
EOT
done
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/trace.conf <<'EOT'
server {
    listen 127.0.0.1:8090;
    location / { proxy_pass http://127.0.0.1:9100; }
}
EOT
systemctl daemon-reload
systemctl enable --now lab-traceapp lab-traceworker nginx >/dev/null 2>&1
sleep 1
