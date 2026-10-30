chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cd /home/student/ansible
chk drifted_named '[ "$(tr -d " \r\n" < /home/student/drift.txt)" = n2 ]'
chk fleet_converged 'ansible-playbook -i localhost, -c local fleet.yml 2>&1 | grep -Eq "changed=0" && for n in n1 n2 n3; do grep -qx "worker_threads=8" /etc/lab/$n.conf || exit 1; done'
chk playbook_untouched 'sha256sum -c /root/.fleet.ref >/dev/null 2>&1'
