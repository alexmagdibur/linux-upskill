install -d /srv/labapi; echo api-ok > /srv/labapi/index.html
cat > /etc/systemd/system/labapi.service <<'EOT'
[Service]
WorkingDirectory=/srv/labapi
ExecStart=/usr/bin/python3 -m http.server 9000 --bind 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/api.conf <<'EOT'
server {
    listen 127.0.0.1:8088;
    location / { proxy_pass http://127.0.0.1:9001; }
}
EOT
systemctl daemon-reload
systemctl enable --now labapi nginx >/dev/null 2>&1
curl -s -m 3 http://127.0.0.1:8088/ >/dev/null
