sudo tee /etc/nginx/conf.d/app.conf > /dev/null <<'EOT'
server {
    listen 80;
    server_name app.lab.test;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name app.lab.test;
    ssl_certificate /etc/lab/tls/app.crt;
    ssl_certificate_key /etc/lab/tls/app.key;
    location / { proxy_pass http://127.0.0.1:9000; }
}
EOT
sudo nginx -t && sudo systemctl reload nginx
