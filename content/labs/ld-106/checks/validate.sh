chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }
probe() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }

chk outbound_works 'curl -s -m 4 -o /dev/null -w "%{http_code}" http://10.82.0.2:8000/ | grep -q 200'
chk still_closed '! probe srv 10.82.0.1 9999 && nft list chain inet filter input | grep -q "policy drop"'
chk explained 'grep -qi established /home/student/why.txt && grep -qi conntrack /home/student/why.txt'
