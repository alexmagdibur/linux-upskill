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

node ok hk0 k0 10.85.0.2/24 10.85.0.1/24
node bad hx0 x0 10.85.1.2/24 10.85.1.1/24
ip -6 addr add fd00:85::1/64 dev hk0 nodad; nsenter --net=/run/netns/ok ip -6 addr add fd00:85::2/64 dev k0 nodad
ip -6 addr add fd00:85:1::1/64 dev hx0 nodad; nsenter --net=/run/netns/bad ip -6 addr add fd00:85:1::2/64 dev x0 nodad
mkdir -p /opt/lab
cat > /opt/lab/listen6.py <<'EOT'
import socket
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
s.bind(("::", 8080)); s.listen(20)
while True:
    c, _ = s.accept(); c.sendall(b"ok\n"); c.close()
EOT
cat > /etc/systemd/system/lab-dual.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/listen6.py
[Install]
WantedBy=multi-user.target
EOT
listener ssh 22 ssh
systemctl daemon-reload; systemctl enable --now lab-dual >/dev/null 2>&1
nft flush ruleset
nft -f - <<'EOT'
table ip filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        ip saddr 10.85.0.0/24 tcp dport 8080 accept
        tcp dport 22 accept
    }
}
table ip6 filter6 {
    chain input {
        type filter hook input priority 0; policy accept;
    }
}
EOT
sleep 1
