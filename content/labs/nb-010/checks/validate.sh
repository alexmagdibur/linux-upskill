chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk head5 '[ "$(cat $H/head5.txt)" = "$(seq -f "event %g ok" 1 5)" ]'
chk tail5 '[ "$(cat $H/tail5.txt)" = "$(seq -f "event %g ok" 36 40)" ]'
chk lines 'grep -qE "^[[:space:]]*40([[:space:]]|$)" $H/lines.txt'
