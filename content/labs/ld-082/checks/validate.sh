chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
R=/home/student/oom_report.txt
lim=$(cat /sys/fs/cgroup/memory.max)
oom=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)
peak=$(cat /sys/fs/cgroup/memory.peak 2>/dev/null)
chk limit '[ "$(grep ^limit_bytes= $R | cut -d= -f2)" = "$lim" ]'
chk oom_kills '[ "$oom" -ge 1 ] && [ "$(grep ^oom_kills= $R | cut -d= -f2)" = "$oom" ]'
chk peak '[ -n "$peak" ] && [ "$(grep ^peak_bytes= $R | cut -d= -f2)" -ge $(( $(cat /sys/fs/cgroup/memory.max) / 2 )) ] && [ "$(grep ^peak_bytes= $R | cut -d= -f2)" -le "$peak" ]'
