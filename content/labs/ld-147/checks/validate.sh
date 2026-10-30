chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
g=/sys/fs/cgroup/labgrp
sleep 2
rep() { grep "^$1=" /home/student/cg.txt | cut -d= -f2 | tr -d ' '; }
chk limits_ok '[ "$(cat $g/memory.max)" = 52428800 ] && [ "$(cat $g/cpu.max)" = "20000 100000" ]'
chk proc_in_group 'for p in $(cat $g/cgroup.procs); do tr "\0" " " < /proc/$p/cmdline; echo; done | grep -q hog.py'
chk throttle_effect '[ "$(awk "/^nr_throttled/{print \$2}" $g/cpu.stat)" -gt 0 ]'
chk report_ok '[ -n "$(rep oom)" ] && [ "$(rep throttled)" -gt 0 ]'
