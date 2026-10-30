chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

p6() { nsenter --net=/run/netns/$1 nc -6 -z -w2 $2 $3; }
p4() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }
chk ok_both 'p4 ok 10.85.0.1 8080 && p6 ok fd00:85::1 8080'
chk bad_blocked_both '! p4 bad 10.85.1.1 8080 && ! p6 bad fd00:85:1::1 8080'
chk ssh_kept 'nft list ruleset | grep -q "dport 22"'
