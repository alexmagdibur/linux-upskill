install -d /var/lib/labapp2/db /var/lib/labapp2/uploads /etc/labapp2 /var/backups/labapp2
echo db > /var/lib/labapp2/db/main.db; echo up1 > /var/lib/labapp2/uploads/photo.jpg; echo cache > /var/lib/labapp2/uploads/cache.tmp
echo cfg > /etc/labapp2/app.conf
cat > /usr/local/bin/lab-backup2.sh <<'EOT'
#!/bin/bash
set -e
tar -czf /var/backups/labapp2/latest.tar.gz --exclude='db' --exclude='*.tmp' /var/lib/labapp2/uploadz /etc/labapp 2>/dev/null || true
EOT
chmod 755 /usr/local/bin/lab-backup2.sh
