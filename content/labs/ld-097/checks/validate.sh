chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk client_ok '[ "$(NS cli curl -s -m 3 http://10.65.0.1:8081/ | tr -d "\n")" = lab-ok ]'
chk not_loopback_only '! ss -ltn | grep ":8081 " | grep -q "127.0.0.1:8081"'
