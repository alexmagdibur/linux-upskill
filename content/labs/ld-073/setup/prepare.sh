mkdir -p /mnt/bytes /mnt/inodes
mount -t tmpfs -o size=2m tmpfs /mnt/bytes
mount -t tmpfs -o size=64m,nr_inodes=40 tmpfs /mnt/inodes
dd if=/dev/zero of=/mnt/bytes/big bs=1M count=3 2>/dev/null || true
i=0; while touch /mnt/inodes/f$i 2>/dev/null; do i=$((i+1)); done
true
