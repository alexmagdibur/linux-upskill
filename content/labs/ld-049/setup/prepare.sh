install -d /opt/lab
cat > /opt/lab/web.py <<'EOT'
import http.server, socketserver

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello from labweb\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8080), H).serve_forever()
EOT
chmod 755 /opt/lab/web.py
