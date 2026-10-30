chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
S() { echo | timeout 8 openssl s_client -connect 127.0.0.1:443 -servername app.lab.test "$@" 2>&1; }
chk chain_verifies 'S -CAfile /etc/lab/ca/root.crt -verify_return_error | grep -q "Verify return code: 0 (ok)"'
chk served_chain_len '[ "$(S -showcerts | grep -c "BEGIN CERTIFICATE")" -ge 2 ]'
