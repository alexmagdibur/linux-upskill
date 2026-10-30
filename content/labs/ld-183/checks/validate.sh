chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cd /home/student/ansible
chk playbook_fixed 'ansible-playbook -i nodes.ini update.yml >/tmp/.upd.out 2>&1'
sleep 4
chk fleet_v2 'for p in 8101 8102 8103; do [ "$(curl -s -m 2 http://127.0.0.1:$p/ | tr -d "\n")" = v2 ] || exit 1; done'
chk fleet_healthy 'for p in 8101 8102 8103; do curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:$p/health | grep -q 200 || exit 1; done'
