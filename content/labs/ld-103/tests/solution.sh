sudo tee /etc/nginx/conf.d/ka.conf > /dev/null <<'EOT'
upstream lab_backend {
    server 127.0.0.1:9200;
    keepalive 8;
}
server {
    listen 127.0.0.1:8095;
    location / {
        proxy_pass http://lab_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
EOT
sudo nginx -t && sudo systemctl reload nginx
