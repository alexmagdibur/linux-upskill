sudo tee /etc/nginx/conf.d/trace.conf > /dev/null <<'EOT'
log_format trace '$remote_addr rid=$request_id "$request"';
server {
    listen 127.0.0.1:8090;
    access_log /var/log/nginx/trace.log trace;
    location / { proxy_pass http://127.0.0.1:9100; }
}
EOT
sudo systemctl reload nginx
