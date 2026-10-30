install -d /etc/lab/ca /etc/lab/tls
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=Lab Root CA" >/dev/null 2>&1

openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/app.key -out /tmp/w.csr -subj "/CN=wrong.example" >/dev/null 2>&1
openssl x509 -req -in /tmp/w.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:wrong.example') -out /etc/lab/tls/app.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/ca.crt; chmod 600 /etc/lab/tls/app.key
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/app.conf <<'EOT'
server {
    listen 443 ssl;
    server_name app.lab.test;
    ssl_certificate /etc/lab/tls/app.crt;
    ssl_certificate_key /etc/lab/tls/app.key;
    location / { return 200 "secure-ok\n"; }
}
EOT
systemctl enable --now nginx >/dev/null 2>&1
sleep 1
