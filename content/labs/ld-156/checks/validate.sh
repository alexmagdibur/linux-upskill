chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
sleep 1
chk syscall_named 'grep -Eqx "(openat|open|read)" <(tr -d " \r" < /home/student/syscall.txt)'
chk unblocked '[ -e /var/lib/labapp/hang-done ]'
chk same_process '[ "$(systemctl show -p MainPID --value labhang)" = "$(cat /var/lib/lab-hang-pid)" ]'
