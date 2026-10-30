chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }

sudo_t() { :; }
: > /var/lib/lab/seen
out=$(NS cli curl -s -m 4 http://10.84.1.1:8080/ | tr -d "\n")
chk dnat_works '[ "$out" = backend ]'
chk client_ip_kept '[ "$(tail -n 1 /var/lib/lab/seen)" = 10.84.1.2 ]'
chk forward_on '[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]'
