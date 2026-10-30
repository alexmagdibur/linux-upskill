useradd -m -s /bin/bash labuser; passwd -l labuser >/dev/null
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 127.0.0.1\nAllowTcpForwarding yes\nGatewayPorts no\n' > /etc/ssh/sshd_config.d/10-lab.conf
mkdir -p /run/sshd; ssh-keygen -A >/dev/null
su - student -c "ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q; ssh-keyscan -t ed25519 127.0.0.1 2>/dev/null > ~/.ssh/known_hosts"
install -d -m 700 -o labuser -g labuser /home/labuser/.ssh
install -m 600 -o labuser -g labuser /home/student/.ssh/id_ed25519.pub /home/labuser/.ssh/authorized_keys
install -d /srv/fwdback; echo backend-ok > /srv/fwdback/index.html
cat > /etc/systemd/system/lab-fwdback.service <<'EOT'
[Service]
WorkingDirectory=/srv/fwdback
ExecStart=/usr/bin/python3 -m http.server 8000 --bind 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now ssh lab-fwdback >/dev/null 2>&1
sleep 1
