chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

F=/home/student/path.txt
v() { grep "^$1=" $F | cut -d= -f2- | tr -d ' '; }
rg=$(ip route get 10.50.1.2)
chk src_dev_ok '[ "$(v src)" = "$(echo "$rg" | grep -o "src [0-9.]*" | cut -d" " -f2)" ] && [ "$(v dev)" = "$(echo "$rg" | grep -o "dev [a-z0-9]*" | cut -d" " -f2)" ]'
chk via_ok '[ "$(v via)" = "$(ip route get 10.50.9.5 | grep -o "via [0-9.]*" | cut -d" " -f2)" ]'
chk mac_ok '[ "$(v mac | tr A-Z a-z)" = "$(NS peer ip -br link show hv1 | awk "{print \$3}")" ]'
