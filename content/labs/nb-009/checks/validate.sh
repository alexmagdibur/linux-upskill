chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
L=/home/student/logs
chk logs_removed '[ ! -e $L/a.log ] && [ ! -e $L/b.log ] && [ ! -e $L/c.log ]'
chk others_kept '[ -f $L/c.log.bak ] && [ -f $L/keep.txt ] && [ -f $L/readme.md ]'
