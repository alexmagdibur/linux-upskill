chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }
probe() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }

chk ssh_only_mgmt 'probe mgmt 10.81.1.1 22 && ! probe cli 10.81.2.1 22'
chk http_only_cli 'probe cli 10.81.2.1 80 && ! probe mgmt 10.81.1.1 80'
chk default_drop_ping 'nft list chain inet filter input | grep -q "policy drop" && NS mgmt ping -c1 -W2 10.81.1.1 && NS cli ping -c1 -W2 10.81.2.1'
chk persisted 'nft -c -f /etc/nftables.conf && grep -q "policy drop" /etc/nftables.conf && grep -q "dport 22" /etc/nftables.conf && grep -q "dport 80" /etc/nftables.conf'
