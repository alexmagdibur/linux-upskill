chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk same_bytes 'cmp -s $E/r1 $E/r2'
chk report_complete '[ "$(wc -l < $E/r1)" = 4 ]'
