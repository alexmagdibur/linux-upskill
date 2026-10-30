chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk jump_works '[ "$(NS client runuser -u student -- ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=8 inner id -un 2>/dev/null | tr -d "\r\n")" = inner ]'
chk no_direct_route '! NS client ping -c1 -W1 10.95.2.2 && [ "$(sysctl -n net.ipv4.ip_forward)" = 0 ]'
chk proxyjump_config 'grep -qiE "^[[:space:]]*(ProxyJump|ProxyCommand)" /home/student/.ssh/config && grep -qi "10.95.2.2" /home/student/.ssh/config'
