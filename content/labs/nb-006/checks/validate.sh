chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
P=/home/student/practice
chk tree '[ -d $P/project/docs ]'
chk data_intact '[ "$(cat $P/keep.txt)" = keep ] && [ "$(cat $P/project/old.txt)" = old ]'
