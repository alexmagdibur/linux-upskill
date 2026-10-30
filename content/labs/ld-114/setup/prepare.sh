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

node client hc c0 10.95.1.2/24 10.95.1.1/24
node inner hi i0 10.95.2.2/24 10.95.2.1/24
nsenter --net=/run/netns/client ip route add default via 10.95.1.1
nsenter --net=/run/netns/inner ip route add default via 10.95.2.1
sysctl -qw net.ipv4.ip_forward=0
useradd -m -s /bin/bash jump; useradd -m -s /bin/bash inner
passwd -l jump >/dev/null; passwd -l inner >/dev/null
mkdir -p /run/sshd /etc/ssh/inner
ssh-keygen -A >/dev/null
ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/inner/host_ed25519
cat > /etc/ssh/inner/sshd_config <<'EOT'
Port 22
ListenAddress 10.95.2.2
HostKey /etc/ssh/inner/host_ed25519
PidFile /run/sshd-inner.pid
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers inner
UsePAM yes
EOT
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 10.95.1.1\nAllowUsers jump student\n' > /etc/ssh/sshd_config.d/10-lab.conf
cat > /etc/systemd/system/sshd-inner.service <<'EOT'
[Service]
ExecStart=/usr/bin/nsenter --net=/run/netns/inner /usr/sbin/sshd -D -f /etc/ssh/inner/sshd_config
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now ssh sshd-inner >/dev/null 2>&1
sleep 1
