sudo rm -f /var/log/labapp/app.log.2022.old /var/log/labapp/app.log.2023.old
sudo tee /etc/logrotate.d/labapp > /dev/null <<'EOT'
/var/log/labapp/app.log {
    daily
    size 1M
    rotate 5
    compress
    missingok
    notifempty
    copytruncate
}
EOT
sleep 2
