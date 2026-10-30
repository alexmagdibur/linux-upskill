{ echo "limit_bytes=$(awk '/MemTotal/{print $2}' /proc/meminfo)"; echo "memtotal_kb=1"; echo "note=память потерялась"; } > ~/mem.txt
