chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }
probe() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }

chk healthcheck_ok 'probe hc 10.83.0.1 8080'
chk others_kept 'nft list chain inet filter input | grep -q "policy drop" && nft list chain inet filter input | grep -q "tcp dport 22" && probe hc 10.83.0.1 22'
chk bad_rule_gone '! nft list chain inet filter input | grep -E "tcp dport 8080" | grep -q drop'
