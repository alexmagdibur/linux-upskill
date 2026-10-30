install -d /srv/labweb
echo lab-ok > /srv/labweb/index.html
ip netns add cli
ip link add hv0 type veth peer name cv0
ip link set cv0 netns cli
ip addr add 10.65.0.1/24 dev hv0; ip link set hv0 up
nsenter --net=/run/netns/cli ip addr add 10.65.0.2/24 dev cv0
nsenter --net=/run/netns/cli ip link set cv0 up
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
cat > /etc/systemd/system/labweb.service <<'EOT'
[Service]
WorkingDirectory=/srv/labweb
ExecStart=/usr/bin/python3 /opt/lab/httpd.py 8081 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labweb >/dev/null 2>&1
sleep 1
