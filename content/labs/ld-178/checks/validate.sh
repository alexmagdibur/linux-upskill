chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cd /home/student/ansible
run() { ansible-playbook -i localhost, -c local site.yml 2>&1; }
r1=$(run); r2=$(run)
sleep 1
chk runs_ok 'echo "$r1" | grep -Eq "failed=0" && echo "$r1" | grep -Eq "unreachable=0"'
chk idempotent 'echo "$r2" | grep -Eq "changed=0" && echo "$r2" | grep -Eq "failed=0"'
chk service_ok '[ "$(curl -s -m 3 http://127.0.0.1:8070/index.html | tr -d "\n")" = hello ]'
