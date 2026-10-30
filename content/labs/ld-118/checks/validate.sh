chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk redirect_301 'h=$(curl -s -m 5 -I -H "Host: app.lab.test" http://127.0.0.1/x); echo "$h" | head -n 1 | grep -q " 301 " && echo "$h" | tr -d "\r" | grep -qi "^location: https://app.lab.test/x$"'
chk https_proxy '[ "$(curl -s -m 5 --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:443:127.0.0.1 https://app.lab.test/ | tr -d "\n")" = backend-ok ]'
chk nginx_valid 'nginx -t'
