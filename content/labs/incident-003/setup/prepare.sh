mkdir -p ~/app
printf 'port=9090\nname=demo-api\n' > ~/app/config.ini
cat > ~/app/server.py <<'EOT'
import http.server, os, socketserver

cfg = {}
base = os.path.dirname(os.path.abspath(__file__))
for line in open(os.path.join(base, "config.ini")):
    if "=" in line:
        key, value = line.strip().split("=", 1)
        cfg[key] = value


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"healthy\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", int(cfg.get("port", "8000"))), Handler).serve_forever()
EOT
setsid nohup python3 ~/app/server.py >/dev/null 2>&1 </dev/null &
sleep 1
