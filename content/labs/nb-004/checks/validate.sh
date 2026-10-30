chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
W=/home/student/work
l1=$(sed -n 1p $W/paths.txt); l2=$(sed -n 2p $W/paths.txt)
chk absolute '[ "$l1" = $W/data/report.txt ]'
chk relative 'cd $W && case "$l2" in /*|"") exit 1;; esac && [ "$(stat -c %i "$l2")" = "$(stat -c %i $W/data/report.txt)" ]'
