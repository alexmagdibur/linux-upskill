install -d /var/lib/lab
printf 'applied_tx=15200\nlag_seconds=95\n' > /var/lib/lab/replica.status
printf 'committed_tx=15920\n' > /var/lib/lab/primary.last
printf 'yes\n' > /var/lib/lab/wal.available
