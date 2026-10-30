chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
R=/home/student/report
chk groups '[ "$(tr -s " \n" "\n\n" < $R/groups.txt | grep -v "^$" | sort | paste -sd" ")" = "devs ops student" ]'
chk uid '[ "$(tr -d "[:space:]" < $R/uid.txt)" = 1000 ]'
chk user1001 '[ "$(tr -d "[:space:]" < $R/user1001.txt)" = validator ]'
chk gid_devs '[ "$(tr -d "[:space:]" < $R/gid_devs.txt)" = 2001 ]'
