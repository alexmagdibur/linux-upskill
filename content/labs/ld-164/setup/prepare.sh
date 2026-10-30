install -d /etc/lab /var/lib/lab /var/backups/lab
printf 'port=8080\n' > /etc/lab/app.conf; printf 'host=db1\n' > /etc/lab/db.conf; printf 'allow=10.0.0.0/24\n' > /etc/lab/acl.conf
cp /etc/lab/*.conf /var/backups/lab/
sha256sum /etc/lab/app.conf /etc/lab/db.conf /etc/lab/acl.conf > /var/lib/lab/baseline.sha256
sha256sum /var/lib/lab/baseline.sha256 > /root/.baseline.ref
printf 'allow=0.0.0.0/0\n' > /etc/lab/acl.conf
