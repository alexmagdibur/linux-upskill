chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
c0=$(curl -s -m 3 http://127.0.0.1:9200/count | tr -d "\n")
for i in $(seq 1 20); do curl -s -m 3 -o /dev/null http://127.0.0.1:8095/; done
c1=$(curl -s -m 3 http://127.0.0.1:9200/count | tr -d "\n")
chk reuse_works '[ -n "$c0" ] && [ -n "$c1" ] && [ $((c1 - c0 - 1)) -le 3 ]'
chk proxy_works '[ "$(curl -s -m 3 http://127.0.0.1:8095/ | tr -d "\n")" = hello ]'
chk upstream_keepalive 'cat /etc/nginx/conf.d/ka.conf | grep -q "keepalive" && grep -q "proxy_http_version 1.1" /etc/nginx/conf.d/ka.conf'
