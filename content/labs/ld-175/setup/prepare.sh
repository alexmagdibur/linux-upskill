install -d /srv/vol/data /srv/vol/conf /var/backups/vol
for i in 1 2 3 4 5; do echo "record $i" > /srv/vol/data/r$i.txt; done
echo "mode=prod" > /srv/vol/conf/app.conf
(cd /srv/vol && find . -type f | sort | xargs sha256sum | sed 's# \./# #' > /var/backups/vol/MANIFEST.sha256)
tar -czf /var/backups/vol/vol-backup.tar.gz -C /srv/vol .
sha256sum /var/backups/vol/vol-backup.tar.gz /var/backups/vol/MANIFEST.sha256 > /root/.vol.ref
rm -rf /srv/vol/*
