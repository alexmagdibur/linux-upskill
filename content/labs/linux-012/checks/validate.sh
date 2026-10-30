chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk exported_var '[ "$(cat $H/env_child.txt)" = production ]'
chk inline_var '[ "$(cat $H/greeting.txt)" = hi ]'
chk hello_in_path '[ -x $H/bin/hello ] && [ "$(cat $H/.hello_out)" = hello ]'
