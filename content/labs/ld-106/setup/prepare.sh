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

node srv hs0 s0 10.82.0.2/24 10.82.0.1/24
install -d /opt/lab
cat > /opt/lab/httpd.py <<'EOT'
import http.server, os, socketserver, sys

class Server(http.server.ThreadingHTTPServer):
    def server_bind(self):  # без обратного DNS-запроса (getfqdn), который в изолированной сети подвисает
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[0], self.server_address[1]

port, bind = int(sys.argv[1]), sys.argv[2]
if len(sys.argv) > 3:
    os.chdir(sys.argv[3])
Server((bind, port), http.server.SimpleHTTPRequestHandler).serve_forever()
EOT
cat > /etc/systemd/system/lab-srvhttp.service <<'EOT'
[Service]
WorkingDirectory=/tmp
ExecStart=/usr/bin/nsenter --net=/run/netns/srv /usr/bin/python3 /opt/lab/httpd.py 8000 10.82.0.2 /tmp
[Install]
WantedBy=multi-user.target
EOT
listener closed 9999 closed
systemctl daemon-reload; systemctl enable --now lab-srvhttp >/dev/null 2>&1
nft flush ruleset
nft add table inet filter
nft add chain inet filter input '{ type filter hook input priority 0; policy drop; }'
nft add rule inet filter input iif lo accept
sleep 1
