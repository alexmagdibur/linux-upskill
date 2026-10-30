chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk success_path '[ "$(cat $E/a)" = "$(printf "first\nsecond\ncleanup")" ]'
chk failure_path '[ "$(cat $E/b)" = "$(printf "first\ncleanup")" ]'
