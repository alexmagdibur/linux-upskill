chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk fails_loudly '[ "$(cat $E/rc1)" != 0 ] && grep -q FAILED $E/st1'
chk success_ok '[ "$(cat $E/rc2)" = 0 ] && grep -q "status: OK" $E/st2 && [ "$(cat /home/student/out/sorted.txt)" = "$(printf "a\nb\nc")" ]'
