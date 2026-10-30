chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk answer '[ "$(tr -d "\n" < /home/student/answer.txt)" = /home/student ]'
