sudo sh -c 'sha256sum /etc/lab/*.conf > /var/lib/lab/baseline.sha256'
echo /etc/lab/acl.conf > ~/tampered.txt
