chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk report 'grep -qi alias $H/report.txt && grep -q "/usr/bin/grep" $H/report.txt'
chk apples '[ "$(cat $H/apples.txt)" = "$(printf "apple pie\ngreen apple")" ]'
