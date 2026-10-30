chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
ok=0
for i in $(seq 1 10); do curl -s -m 4 --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:8443:127.0.0.1 https://app.lab.test:8443/ | grep -q ok && ok=$((ok+1)); done
chk all_requests_ok '[ "$ok" = 10 ]'
chk both_new 'for p in 9301 9302; do echo | openssl s_client -connect 127.0.0.1:$p -servername app.lab.test -CAfile /etc/lab/ca/ca.crt -verify_return_error 2>&1 | grep -q "Verify return code: 0 (ok)" || exit 1; done'
