echo "+cpu +memory" | sudo tee /sys/fs/cgroup/cgroup.subtree_control > /dev/null 2>&1 || true
sudo mkdir -p /sys/fs/cgroup/labgrp
echo 52428800 | sudo tee /sys/fs/cgroup/labgrp/memory.max > /dev/null
echo "20000 100000" | sudo tee /sys/fs/cgroup/labgrp/cpu.max > /dev/null
sudo sh -c 'nohup python3 /opt/lab/hog.py >/dev/null 2>&1 & echo $! > /sys/fs/cgroup/labgrp/cgroup.procs'
sleep 6
o=$(awk '/^oom_kill/{print $2}' /sys/fs/cgroup/labgrp/memory.events)
t=$(awk '/^nr_throttled/{print $2}' /sys/fs/cgroup/labgrp/cpu.stat)
printf 'oom=%s\nthrottled=%s\n' "$o" "$t" > ~/cg.txt
