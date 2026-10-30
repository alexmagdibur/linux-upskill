chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk found_file '[ "$(tr -d " \r" < /home/student/tampered.txt)" = /etc/lab/acl.conf ]'
chk restored 'sha256sum -c /var/lib/lab/baseline.sha256 >/dev/null 2>&1'
chk baseline_untouched 'sha256sum -c /root/.baseline.ref >/dev/null 2>&1'
