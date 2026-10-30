sudo tee /etc/logrotate.d/lablogger > /dev/null <<'EOT'
/var/log/lab/app.log {
    rotate 3
    missingok
    nocompress
    postrotate
        /usr/bin/systemctl kill -s HUP lablogger.service
    endscript
}
EOT
