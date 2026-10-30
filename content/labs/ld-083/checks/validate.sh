chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cg=/sys/fs/cgroup/system.slice/labburn.service
thr() { awk '/^nr_throttled/{print $2}' $cg/cpu.stat; }
a=$(thr); sleep 3; b=$(thr)
rep=$(grep ^nr_throttled= /home/student/throttle.txt | cut -d= -f2 | tr -d ' ')
chk limits_set '[ "$(systemctl show -p CPUQuotaPerSecUSec --value labburn)" = 250ms ] && [ "$(systemctl show -p MemoryMax --value labburn)" = 67108864 ]'
chk really_throttled '[ "$b" -gt "$a" ]'
chk report_ok '[ -n "$rep" ] && [ "$rep" -gt 0 ] && [ "$rep" -le "$b" ]'
