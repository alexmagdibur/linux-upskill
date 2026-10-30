sudo tee /usr/local/bin/lab-backup2.sh > /dev/null <<'EOT'
#!/bin/bash
set -e
tar -czf /var/backups/labapp2/latest.tar.gz --exclude='*.tmp' /var/lib/labapp2 /etc/labapp2
tar -tzf /var/backups/labapp2/latest.tar.gz > /dev/null
EOT
