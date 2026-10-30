cat > /etc/dnsmasq-auth.conf <<'EOT'
port=5300
listen-address=127.0.0.2
bind-interfaces
no-resolv
no-hosts
host-record=app.lab.test,10.20.0.5
local-ttl=3600
pid-file=/run/dnsmasq-auth.pid
EOT
cat > /etc/dnsmasq-cache.conf <<'EOT'
port=5353
listen-address=127.0.0.1
bind-interfaces
no-resolv
no-hosts
server=127.0.0.2#5300
cache-size=200
min-cache-ttl=3600
pid-file=/run/dnsmasq-cache.pid
EOT
for u in auth cache; do
cat > /etc/systemd/system/dnsmasq-$u.service <<EOT
[Service]
ExecStart=/usr/sbin/dnsmasq -k --conf-file=/etc/dnsmasq-$u.conf
[Install]
WantedBy=multi-user.target
EOT
done
systemctl daemon-reload
systemctl enable --now dnsmasq-auth >/dev/null 2>&1; sleep 1
systemctl enable --now dnsmasq-cache >/dev/null 2>&1; sleep 1
dig +short @127.0.0.1 -p 5353 app.lab.test > /dev/null
sed -i 's/host-record=app.lab.test,10.20.0.5/host-record=app.lab.test,10.20.0.55/' /etc/dnsmasq-auth.conf
systemctl restart dnsmasq-auth
sleep 1
