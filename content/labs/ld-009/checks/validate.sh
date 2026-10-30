chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk stdout '[ "$(cat $H/out.txt)" = "stdout: ready" ]'
chk stderr '[ "$(cat $H/err.txt)" = "stderr: warning" ]'
chk rc '[ "$(tr -d "[:space:]" < $H/rc.txt)" = 3 ]'
