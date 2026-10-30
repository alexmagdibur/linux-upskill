sudo tee /etc/logrotate.d/lablogger > /dev/null <<'EOT'
/var/log/lab/app.log {
    rotate 3
    missingok
    nocompress
}
EOT
