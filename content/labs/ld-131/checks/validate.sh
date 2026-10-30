chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk empty_dir_rejected '[ -f $E/sA/keep ] && [ "$(cat $E/rcA)" != 0 ]'
chk missing_dir_rejected '[ -f $E/sB/keep ] && [ "$(cat $E/rcB)" != 0 ]'
chk valid_cleaned '[ "$(cat $E/rcC)" = 0 ] && [ -z "$(ls -A "$E/target dir")" ] && [ -f $E/sC/keep ]'
