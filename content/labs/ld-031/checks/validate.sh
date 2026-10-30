chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
as() { runuser -u "$1" -- sh -c "$2"; }

chk can_restart 'as oper "sudo -n /usr/bin/systemctl restart labsvc.service"'
chk others_denied '! as oper "sudo -n /usr/bin/systemctl restart other.service" && ! as oper "sudo -n /usr/bin/id" && ! as oper "sudo -n /usr/bin/systemctl stop labsvc.service"'
chk syntax_perms 'visudo -c >/dev/null 2>&1 && f=$(grep -l "^oper" /etc/sudoers.d/* | head -n 1) && [ -n "$f" ] && [ "$(stat -c %a $f)" = 440 ]'
chk no_blanket_all '! sudo -l -U oper 2>/dev/null | grep -Eq "NOPASSWD: ALL|\(ALL\) ALL"'
