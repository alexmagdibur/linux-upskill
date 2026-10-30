chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk installed_prefix '[ "$(/opt/hello-lab/bin/hello-lab)" = "hello from lab" ]'
chk usr_clean '! find /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /bin /sbin -name hello-lab -type f 2>/dev/null | grep -q .'
chk on_path '[ "$(runuser -l student -c "hello-lab")" = "hello from lab" ]'
