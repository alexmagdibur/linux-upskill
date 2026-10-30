chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }
probe() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }

chk metadata_blocked '! probe wl 169.254.169.254 80'
chk app_open 'probe wl 10.86.0.1 8080'
chk host_still_ok 'nc -z -w2 169.254.169.254 80'
