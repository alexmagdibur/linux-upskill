chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
a=$(dig +short +time=2 +tries=1 @127.0.0.1 -p 5353 app.lab.test)
ttl=$(dig +noall +answer +ttlid +time=2 +tries=1 @127.0.0.1 -p 5353 app.lab.test | awk '{print $2}' | head -n 1)
big=$(grep -hE "^(min-cache-ttl|local-ttl)=" /etc/dnsmasq-cache.conf /etc/dnsmasq-auth.conf | awk -F= '$2>60{n++} END{print n+0}')
chk new_answer '[ "$a" = 10.20.0.55 ]'
chk ttl_sane '[ "$big" = 0 ]'
chk ttl_in_answer '[ -n "$ttl" ] && [ "$ttl" -le 60 ]'
