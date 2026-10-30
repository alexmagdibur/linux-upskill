chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk core '[ "$(tr -d "\n" < $H/paths/core.txt)" = $H/project/src/app/core ]'
chk parent '[ "$(tr -d "\n" < $H/paths/parent.txt)" = $H/project/src/app ]'
chk project_intact '[ "$(cat $H/project/src/app/core/main.py)" = "print(1)" ] && [ "$(cat $H/project/README.md)" = "# demo" ]'
