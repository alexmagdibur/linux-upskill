install -d /etc/lab/ca /etc/lab/tls
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout root.key -out root.crt -days 3650 -subj "/CN=Lab Root" >/dev/null 2>&1
openssl req -new -newkey rsa:2048 -nodes -keyout inter.key -out inter.csr -subj "/CN=Lab Intermediate" >/dev/null 2>&1
openssl x509 -req -in inter.csr -CA root.crt -CAkey root.key -CAcreateserial -days 3000 -extfile <(printf 'basicConstraints=critical,CA:TRUE\nkeyUsage=keyCertSign,cRLSign') -out inter.crt >/dev/null 2>&1
openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/leaf.key -out /tmp/leaf.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
openssl x509 -req -in /tmp/leaf.csr -CA inter.crt -CAkey inter.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/leaf.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/*.crt /etc/lab/tls/leaf.crt; chmod 600 /etc/lab/tls/leaf.key
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/app.conf <<'EOT'
server {
    listen 443 ssl;
    server_name app.lab.test;
    ssl_certificate /etc/lab/tls/leaf.crt;
    ssl_certificate_key /etc/lab/tls/leaf.key;
    location / { return 200 "chain-ok\n"; }
}
EOT
systemctl enable --now nginx >/dev/null 2>&1
sleep 1
