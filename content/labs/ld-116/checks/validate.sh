chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk local_forward '[ "$(curl -s -m 4 http://127.0.0.1:9000/ | tr -d "\n")" = backend-ok ] && ss -ltnp | grep ":9000 " | grep -q ssh'
chk remote_forward '[ "$(curl -s -m 4 http://127.0.0.1:9100/ | tr -d "\n")" = backend-ok ] && ss -ltnp | grep ":9100 " | grep -q sshd'
chk sides_ok 'grep -qx "L_listens=client" /home/student/fwd.txt && grep -qx "R_listens=server" /home/student/fwd.txt'
