pid=$(pgrep -f probe.py | head -n 1)
{
  echo "cwd=$(readlink /proc/$pid/cwd)"
  echo "token=$(tr '\0' '\n' < /proc/$pid/environ | grep ^PROBE_TOKEN= | cut -d= -f2)"
  echo "open_file=$(ls -l /proc/$pid/fd | grep held.txt | sed 's/.* -> //')"
  echo "nofile_soft=$(awk '/Max open files/{print $4}' /proc/$pid/limits)"
  echo "cgroup=$(head -n 1 /proc/$pid/cgroup)"
} > ~/proc_report.txt
