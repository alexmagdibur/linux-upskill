sudo tar -xzf /var/backups/vol/vol-backup.tar.gz -C /srv/vol
cd /srv/vol && sha256sum -c /var/backups/vol/MANIFEST.sha256
