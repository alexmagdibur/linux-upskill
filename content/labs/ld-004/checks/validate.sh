chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk child_sees '[ "$(cat $H/child_out.txt)" = mode=prod ]'
chk not_persistent '[ "$(cat $H/.ex/fresh)" = unset ]'
