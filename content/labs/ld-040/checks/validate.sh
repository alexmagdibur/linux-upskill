chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
R=/home/student/mem_report.txt
pid=$(systemctl show -p MainPID --value labmem)
rss=$(awk '/VmRSS/{print $2}' /proc/$pid/status); vsz=$(awk '/VmSize/{print $2}' /proc/$pid/status)
val() { grep "^$1=" $R | cut -d= -f2- | tr -d ' '; }
near() { python3 -c "import sys; a,b,t=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3]); sys.exit(0 if abs(a-b)<=t*b else 1)" "$1" "$2" "$3"; }
chk rss_ok 'near "$(val rss_kb)" "$rss" 0.20'
chk vsz_ok 'near "$(val vsz_kb)" "$vsz" 0.10 && [ "$(val vsz_kb)" -gt $(( $(val rss_kb) * 3 )) ]'
chk cached_ok '[ "$(val cached_kb)" -ge 20000 ]'
chk note_ok 'grep ^note= $R | grep -qiE "cache|кэш|кеш"'
