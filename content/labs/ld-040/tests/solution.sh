pid=$(systemctl show -p MainPID --value labmem)
{
  echo "rss_kb=$(awk '/VmRSS/{print $2}' /proc/$pid/status)"
  echo "vsz_kb=$(awk '/VmSize/{print $2}' /proc/$pid/status)"
  echo "cached_kb=$(awk '/^Cached:/{print $2}' /proc/meminfo)"
  echo "note=VSZ включает зарезервированное, но не тронутое адресное пространство, RSS — реально занятые страницы; page cache общий и в RSS не входит"
} > ~/mem_report.txt
