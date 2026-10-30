install -d /opt/lab /etc/lab
printf '22\n8080\n5432\n' > /etc/lab/allowed-ports
cat > /opt/lab/listener.py <<'EOT'
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((sys.argv[1], int(sys.argv[2])))
s.listen(5)
while True:
    time.sleep(60)
EOT
mk() { cat > /etc/systemd/system/$1.service <<EOT
[Service]
ExecStart=/usr/bin/python3 /opt/lab/listener.py $2 $3
[Install]
WantedBy=multi-user.target
EOT
}
mk labweb 0.0.0.0 8080; mk labdb 127.0.0.1 5432; mk miner 0.0.0.0 31337; mk debugd 0.0.0.0 9229
systemctl daemon-reload
systemctl enable --now labweb labdb miner debugd >/dev/null 2>&1
sleep 2
