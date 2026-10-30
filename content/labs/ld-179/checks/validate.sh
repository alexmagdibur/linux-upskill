chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cd /home/student/ansible
run() { ansible-playbook -i localhost, -c local app.yml "$@" 2>&1; }
pid() { systemctl show -p MainPID --value labsvc2; }
listen() { ss -ltn | grep -q "127.0.0.1:$1 "; }
run >/dev/null; sleep 1; p1=$(pid); l1=0; listen 8071 && l1=1
run -e app_port=8072 >/dev/null; sleep 1; p2=$(pid); l2=0; listen 8072 && l2=1
run -e app_port=8072 >/dev/null; sleep 1; p3=$(pid)
chk syntax_ok 'ansible-playbook -i localhost, -c local app.yml --syntax-check'
chk renders_port '[ "$l1" = 1 ] && [ "$l2" = 1 ] && grep -qx "port=8072" /etc/labsvc2/app.conf'
chk restart_on_change '[ "$p1" != "$p2" ]'
chk no_restart_same '[ "$p2" = "$p3" ] && [ "$p2" != 0 ]'
