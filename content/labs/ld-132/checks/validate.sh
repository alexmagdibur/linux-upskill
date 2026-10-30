chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk no_double_run '[ "$(tr -d " " < $E/c1)" = 1 ]'
chk no_stale_lock '[ "$(tr -d " " < $E/c2)" = 2 ]'
