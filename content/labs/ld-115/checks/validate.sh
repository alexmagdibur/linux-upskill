chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk login_ok 'runuser -u student -- ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 labuser@127.0.0.1 echo ok | grep -qx ok'
chk strict_on '[ "$(sshd -T | awk "/^strictmodes/{print \$2}")" = yes ]'
chk perms_safe '[ $(( 0$(stat -c %a /home/labuser) & 0022 )) -eq 0 ] && [ "$(stat -c %a /home/labuser/.ssh)" = 700 ] && [ $(( 0$(stat -c %a /home/labuser/.ssh/authorized_keys) & 0077 )) -eq 0 ]'
