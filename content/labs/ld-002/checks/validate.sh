chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
W=/home/student/work
chk created '[ -d $W/proj/reports/today ] && [ ! -e $W/reports ]'
chk neighbors_intact 'pgrep -f "sleep 3601" && [ "$(cat $W/other/keep.txt)" = keep ] && [ ! -e $W/other/reports ]'
