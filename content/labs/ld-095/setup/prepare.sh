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

node peer ha p_a 10.91.0.2/24 10.91.0.1/24
ip link add hb type veth peer name p_b
ip link set p_b netns peer
ip addr add 10.92.0.1/24 dev hb; ip link set hb up
nsenter --net=/run/netns/peer ip addr add 10.92.0.2/24 dev p_b
nsenter --net=/run/netns/peer ip link set p_b up
# запросы с 10.92.0.2 к 10.91.0.1 уходят через сеть A (политика по адресу источника), ответ машина шлёт через B
nsenter --net=/run/netns/peer ip rule add from 10.92.0.2 lookup 100
nsenter --net=/run/netns/peer ip route add 10.91.0.0/24 dev p_a table 100
nsenter --net=/run/netns/peer sysctl -qw net.ipv4.conf.all.rp_filter=1 net.ipv4.conf.p_a.rp_filter=1 net.ipv4.conf.p_b.rp_filter=1
sysctl -qw net.ipv4.conf.all.rp_filter=0 net.ipv4.conf.default.rp_filter=0
ip route add 10.92.0.2/32 dev hb
listener web 8080 asym-ok
