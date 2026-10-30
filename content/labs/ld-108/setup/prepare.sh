node() { # ns hostif nsif nsaddr hostaddr
  ip netns add $1; ip link add $2 type veth peer name $3; ip link set $3 netns $1
  ip addr add $5 dev $2; ip link set $2 up
  nsenter --net=/run/netns/$1 ip addr add $4 dev $3
  nsenter --net=/run/netns/$1 ip link set $3 up; nsenter --net=/run/netns/$1 ip link set lo up
}
listener() { # имя порт [текст]
  mkdir -p /opt/lab
  cat > /opt/lab/listen_$1.py <<EOT
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", $2)); s.listen(20)
while True:
    c, _ = s.accept(); c.settimeout(0.5)
    try:
        c.recv(1024)
    except OSError:
        pass
    c.sendall(b"${3:-$1}\n"); c.close()
EOT
  cat > /etc/systemd/system/lab-$1.service <<EOT
[Service]
ExecStart=/usr/bin/python3 /opt/lab/listen_$1.py
[Install]
WantedBy=multi-user.target
EOT
  systemctl daemon-reload; systemctl enable --now lab-$1 >/dev/null 2>&1
}

node cli hc1 c1 10.84.1.2/24 10.84.1.1/24
node be hb1 b1 10.84.2.2/24 10.84.2.1/24
nsenter --net=/run/netns/cli ip route add default via 10.84.1.1
nsenter --net=/run/netns/be ip route add default via 10.84.2.1
sysctl -qw net.ipv4.ip_forward=0
install -d /opt/lab /var/lib/lab
cat > /opt/lab/be.py <<'EOT'
import http.server, socketserver

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with open("/var/lib/lab/seen", "a") as f:
            f.write(self.client_address[0] + "\n")
        body = b"backend\n"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass

socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("10.84.2.2", 80), H).serve_forever()
EOT
cat > /etc/systemd/system/lab-be.service <<'EOT'
[Service]
ExecStart=/usr/bin/nsenter --net=/run/netns/be /usr/bin/python3 /opt/lab/be.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload; systemctl enable --now lab-be >/dev/null 2>&1
nft flush ruleset
sleep 1
