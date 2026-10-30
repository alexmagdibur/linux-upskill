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

node wl hw0 w0 10.86.0.2/24 10.86.0.1/24
nsenter --net=/run/netns/wl ip route add 169.254.169.254/32 via 10.86.0.1
ip link add meta0 type dummy; ip addr add 169.254.169.254/32 dev meta0; ip link set meta0 up
mkdir -p /opt/lab
cat > /opt/lab/meta.py <<'EOT'
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("169.254.169.254", 80)); s.listen(20)
while True:
    c, _ = s.accept(); c.sendall(b"TOKEN-SECRET\n"); c.close()
EOT
cat > /etc/systemd/system/lab-meta.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/meta.py
[Install]
WantedBy=multi-user.target
EOT
listener app 8080 app
systemctl daemon-reload; systemctl enable --now lab-meta >/dev/null 2>&1
nft flush ruleset
sleep 1
