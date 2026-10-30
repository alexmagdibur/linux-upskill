chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
L=/var/lib/lab/ledger.txt
chk no_double_run '[ "$(wc -l < /tmp/ledger.test)" = 1 ]'
chk data_repaired '[ "$(sort $L | uniq -d | wc -l)" = 0 ] && [ "$(wc -l < $L)" = 4 ]'
