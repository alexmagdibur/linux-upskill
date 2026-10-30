sudo tee /etc/nginx/conf.d/app.conf > /dev/null <<'EOT'
server {
    listen 80;
    location / { proxy_pass http://127.0.0.1:9000; }
}
EOT
sudo systemctl reload nginx
