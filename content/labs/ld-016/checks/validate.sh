chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk_counts() { python3 - <<'EOT'
import json
try:
    got = json.load(open("/home/student/.ex/rep/out.json"))
except Exception:
    print("BAD"); raise SystemExit
print("OK" if got == {"200": 180000, "404": 60000, "500": 60000} else "BAD")
EOT
}
chk counts_ok '[ "$(cat $E/rc_ok)" = 0 ] && [ "$(chk_counts)" = OK ]'
chk failure_keeps_old '[ "$(cat $E/rc_bad)" = 2 ] && [ "$(cat $E/rep/out2.json)" = OLD ]'
chk no_temp_leftovers '[ "$(sort $E/listing | paste -sd,)" = "bad.log,big.log,out.json,out2.json" ]'
