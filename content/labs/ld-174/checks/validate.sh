chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
v() { grep "^$1=" /home/student/decision.txt | cut -d= -f2- | tr -d ' '; }
chk lost_ok '[ "$(v lost_tx)" = 720 ]'
chk action_ok '[ "$(v action)" = catchup ]'
