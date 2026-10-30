b=$(df -k --output=target,avail /mnt/bytes /mnt/inodes | awk 'NR>1 && $2<=4 {print $1}')
i=$(df --output=target,iavail /mnt/bytes /mnt/inodes | awk 'NR>1 && $2==0 {print $1}')
printf 'bytes_full=%s\ninodes_full=%s\n' "$b" "$i" > ~/diag.txt
