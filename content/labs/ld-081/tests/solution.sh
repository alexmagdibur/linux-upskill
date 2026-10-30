lim=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
{ echo "limit_bytes=$lim"; echo "memtotal_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo)"; echo "note=MemTotal — память хоста, а предел процесса задаёт cgroup; page cache входит в used, но освобождается при нехватке"; } > ~/mem.txt
