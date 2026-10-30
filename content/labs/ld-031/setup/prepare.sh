useradd -m oper
for u in labsvc other; do
cat > /etc/systemd/system/$u.service <<EOT
[Service]
ExecStart=/usr/bin/sleep infinity
EOT
done
systemctl daemon-reload
systemctl start labsvc other
