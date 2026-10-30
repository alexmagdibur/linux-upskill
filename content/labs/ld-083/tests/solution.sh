sudo systemctl set-property labburn CPUQuota=25% MemoryMax=64M
sleep 4
echo "nr_throttled=$(awk '/^nr_throttled/{print $2}' /sys/fs/cgroup/system.slice/labburn.service/cpu.stat)" > ~/throttle.txt
