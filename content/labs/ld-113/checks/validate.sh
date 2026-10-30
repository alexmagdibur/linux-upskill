chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
S="runuser -u student --"
chk login_ok '$S ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 labuser@127.0.0.1 echo ok | grep -qx ok'
chk perms_ok '[ "$(stat -c %a /home/student/.ssh/id_ed25519)" = 600 ] && [ "$(stat -c %a /home/labuser/.ssh/authorized_keys)" = 600 ] && [ "$(stat -c %U /home/labuser/.ssh/authorized_keys)" = labuser ] && [ "$(stat -c %a /home/labuser/.ssh)" = 700 ]'
srv=$(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $2}')
chk hostkey_pinned 'ssh-keygen -lf /home/student/.ssh/known_hosts | awk "{print \$2}" | grep -qx "$srv"'
