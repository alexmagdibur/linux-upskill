chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
R=/home/student/proc_report.txt
pid=$(pgrep -f 'probe.py' | head -n 1)
soft=$(awk '/Max open files/{print $4}' /proc/$pid/limits)
cg=$(cat /proc/$pid/cgroup | head -n 1)
chk cwd '[ "$(grep ^cwd= $R | cut -d= -f2-)" = /home/student/probe_dir ]'
chk token '[ "$(grep ^token= $R | cut -d= -f2-)" = xyz123 ]'
chk open_file '[ "$(grep ^open_file= $R | cut -d= -f2-)" = /home/student/probe_dir/held.txt ]'
chk limits_cgroup '[ "$(grep ^nofile_soft= $R | cut -d= -f2-)" = "$soft" ] && [ "$(grep ^cgroup= $R | head -n 1 | cut -d= -f2-)" = "$cg" ]'
