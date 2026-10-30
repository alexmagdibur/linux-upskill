chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
F=/home/student/rpo.txt
v() { grep "^$1=" $F | cut -d= -f2- | tr -d ' '; }
chk rpo_ok '[ "$(v rpo_minutes)" = 17 ]'
chk rto_ok '[ "$(v rto_minutes)" = 39 ]'
chk goals_ok '[ "$(v rpo_met)" = no ] && [ "$(v rto_met)" = no ]'
