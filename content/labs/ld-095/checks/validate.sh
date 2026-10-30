chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

chk request_works '[ "$(NS peer curl --http0.9 --interface 10.92.0.2 -s -m 3 http://10.91.0.1:8080/ | tr -d "\n")" = asym-ok ]'
chk routes_unchanged '{ NS peer ip -o route; ip route; NS peer ip route show table 100; } | grep -q "10.92.0.2 dev hb" && NS peer ip rule | grep -q "from 10.92.0.2 lookup 100"'
chk rp_loose '[ "$(NS peer sysctl -n net.ipv4.conf.p_b.rp_filter)" != 1 ] || [ "$(NS peer sysctl -n net.ipv4.conf.all.rp_filter)" = 2 ]'
