chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex; A=/home/student/srv/app
chk exit_codes '[ "$(cat $E/rc1)" = 0 ] && [ "$(cat $E/rc2)" = 0 ]'
chk same_state '[ -s $E/s1 ] && cmp -s $E/s1 $E/s2'
chk content_ok '[ "$(grep -cx port=8080 $A/app.conf)" = 1 ] && [ "$(grep -cx alice $A/users.txt)" = 1 ] && [ "$(grep -cx bob $A/users.txt)" = 1 ] && [ "$(cat $A/data.txt)" = keep-me ]'
