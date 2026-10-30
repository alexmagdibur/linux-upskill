chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
a=$(ip -4 -o addr show dev hv0 | awk '{print $4}')
chk addr_ok '[ "${a##*/}" = 24 ] && [ "${a%.*}" = 10.60.0 ] && [ "${a%/*}" != 10.60.0.1 ] && [ "${a%/*}" != 10.60.0.0 ] && [ "${a%/*}" != 10.60.0.255 ]'
chk only_one_addr '[ "$(ip -4 -o addr show dev hv0 | wc -l)" = 1 ]'
chk gw_pingable 'ping -c1 -W2 10.60.0.1'
