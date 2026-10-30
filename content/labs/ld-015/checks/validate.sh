chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
L=/home/student/logs
chk secrets_gone '! grep -qE "tok_ABC123|hunter2|sk_live_99XYZ|tok_QRS789|p4ssw0rd" $L/sanitized.log'
chk structure_kept '[ "$(wc -l < $L/sanitized.log)" = "$(wc -l < $L/app.log)" ] && [ "$(grep -o "req=r[0-9]*" $L/sanitized.log)" = "$(grep -o "req=r[0-9]*" $L/app.log)" ]'
chk keys_kept '[ "$(grep -o "[a-z_]*=\[REDACTED\]" $L/sanitized.log | wc -l)" = 5 ] && grep -q "token=\[REDACTED\]" $L/sanitized.log && grep -q "password=\[REDACTED\]" $L/sanitized.log && grep -q "api_key=\[REDACTED\]" $L/sanitized.log'
