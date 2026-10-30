{
  echo "limit_bytes=$(cat /sys/fs/cgroup/memory.max)"
  echo "oom_kills=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)"
  echo "peak_bytes=$(cat /sys/fs/cgroup/memory.peak)"
} > ~/oom_report.txt
