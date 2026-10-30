chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk copied '[ "$(cat $H/backup/report.txt)" = Q3 ] && [ "$(cat $H/files/report.txt)" = Q3 ]'
chk renamed '[ "$(cat $H/files/final.txt)" = v1 ] && [ ! -e $H/files/draft.txt ]'
