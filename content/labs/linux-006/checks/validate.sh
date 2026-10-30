chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk ips_unique '[ "$(cat $H/ips.txt)" = "$(printf "192.168.1.%s\n" 1 2 3 4 5 6 7)" ]'
chk count404 '[ "$(tr -d "[:space:]" < $H/count404.txt)" = 12 ]'
chk appended '[ "$(cat $H/data/report.txt)" = "$(printf "start\ndone")" ]'
chk stderr_redirect 'grep -q "No such file or directory" $H/err.txt'
