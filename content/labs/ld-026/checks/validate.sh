chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
V=/home/student/exp/vault
chk dir_has_x '[ $(( 0$(stat -c %a $V) & 0100 )) -ne 0 ]'
chk answer 'grep -q "before=644" /home/student/exp/answer.txt && grep -q "after=$(stat -c %a $V)" /home/student/exp/answer.txt'
chk access_works '[ "$(cat /home/student/.ex/cat.out)" = note ]'
