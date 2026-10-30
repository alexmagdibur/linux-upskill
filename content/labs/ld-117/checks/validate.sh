chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk verified_https '[ "$(curl -s -m 5 --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:443:127.0.0.1 https://app.lab.test/ | tr -d "\n")" = secure-ok ]'
chk san_present 'openssl x509 -in /etc/lab/tls/app.crt -noout -ext subjectAltName | grep -q "DNS:app.lab.test"'
