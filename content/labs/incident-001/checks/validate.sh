chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
A=/home/student/app
chk starts 'grep -q "started OK" $A/logs/app.log'
chk start_executable '[ $(( 0$(stat -c %a $A/start.sh) & 0100 )) -ne 0 ]'
chk script_unchanged 'grep -qx "exec python3 app.py" $A/start.sh && [ "$(wc -l < $A/start.sh)" = 3 ]'
chk no_world_write '[ $(( 0$(stat -c %a $A/logs) & 0002 )) -eq 0 ] && [ $(( 0$(stat -c %a $A/start.sh) & 0002 )) -eq 0 ] && [ $(( 0$(stat -c %a $A) & 0002 )) -eq 0 ]'
