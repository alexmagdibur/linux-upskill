install -d /etc/lab/ca /etc/lab/tls
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=Lab Root CA" >/dev/null 2>&1

openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/app.key -out /tmp/a.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
openssl x509 -req -in /tmp/a.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/app.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/ca.crt /etc/lab/tls/app.crt; chmod 640 /etc/lab/tls/app.key; chgrp www-data /etc/lab/tls/app.key
rm -f /etc/nginx/sites-enabled/default
install -d /srv/labback; echo backend-ok > /srv/labback/index.html
cat > /etc/systemd/system/labback.service <<'EOT'
[Service]
WorkingDirectory=/srv/labback
ExecStart=/usr/bin/python3 -m http.server 9000 --bind 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labback nginx >/dev/null 2>&1
sleep 1
