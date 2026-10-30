chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
mon_start() { ( while :; do h=0; for p in 8101 8102 8103; do curl -s -m 1 -o /dev/null -w '%{http_code}' http://127.0.0.1:$p/health | grep -q 200 && h=$((h+1)); done; echo $h >> /tmp/.healthy.log; sleep 0.2; done ) & echo $! > /tmp/.mon.pid; }
mon_stop() { kill $(cat /tmp/.mon.pid) 2>/dev/null; }

cd /home/student/ansible
for n in 1 2 3; do echo v1 > /etc/labnode/$n.version; done
systemctl restart labnode@1 labnode@2 labnode@3; sleep 4
: > /tmp/.healthy.log; mon_start
ansible-playbook -i nodes.ini rolling.yml >/tmp/.rolling.out 2>&1
sleep 1; mon_stop
min=$(sort -n /tmp/.healthy.log | head -n 1)
chk all_updated '[ "$(cat /etc/labnode/1.version /etc/labnode/2.version /etc/labnode/3.version | sort -u)" = v2 ] && for p in 8101 8102 8103; do [ "$(curl -s -m 2 http://127.0.0.1:$p/ | tr -d "\n")" = v2 ] || exit 1; done'
chk capacity_kept '[ -n "$min" ] && [ "$min" -ge 2 ]'
chk serial_defined 'grep -qE "serial:[[:space:]]*1" rolling.yml && grep -qE "/health" rolling.yml'
