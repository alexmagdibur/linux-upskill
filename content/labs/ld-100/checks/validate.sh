chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk cause_ok '[ "$(tr -d " \r\n" < /home/student/cause.txt | tr A-Z a-z)" = refused ]'
chk proxy_ok '[ "$(curl -s -m 5 http://127.0.0.1:8088/ | tr -d "\n")" = api-ok ]'
