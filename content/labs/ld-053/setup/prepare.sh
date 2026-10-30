install -d /opt/lab /var/lib/lab
printf '#!/bin/bash\ndate +%%F-%%T >> /var/lib/lab/backup.log\n' > /opt/lab/backup.sh
chmod 755 /opt/lab/backup.sh
cat > /etc/systemd/system/labbackup.service <<'EOT'
[Unit]
Description=Lab backup

[Service]
Type=oneshot
ExecStart=/opt/lab/backup.sh
EOT
systemctl daemon-reload
