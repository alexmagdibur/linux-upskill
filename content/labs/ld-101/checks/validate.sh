chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
q() { dig +short +time=2 +tries=1 @127.0.0.1 -p 5353 "$@"; }
chk a_aaaa '[ "$(q web.lab.test A)" = 10.20.0.10 ] && [ "$(q web.lab.test AAAA)" = fd00::10 ]'
chk cname_ok 'q www.lab.test CNAME | grep -qx "web.lab.test."'
chk nxdomain_ok 'dig @127.0.0.1 -p 5353 +time=2 +tries=1 blocked.lab.test A | grep -q "status: NXDOMAIN"'
