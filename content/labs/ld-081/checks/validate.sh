chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
lim=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
tot=$(awk '/MemTotal/{print $2}' /proc/meminfo)
chk limit '[ "$(grep ^limit_bytes= /home/student/mem.txt | cut -d= -f2)" = "$lim" ]'
chk memtotal '[ "$(grep ^memtotal_kb= /home/student/mem.txt | cut -d= -f2)" = "$tot" ]'
chk note 'grep ^note= /home/student/mem.txt | grep -qiE "cache|кэш|кеш"'
