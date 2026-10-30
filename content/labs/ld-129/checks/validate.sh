chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
chk help_ok '[ "$(cat $E/h.rc)" = 0 ] && grep -q Usage $E/h.out'
chk no_args '[ "$(cat $E/n.rc)" = 2 ] && grep -q Usage $E/n.err'
chk archive_made '[ "$(cat $E/ok.rc)" = 0 ] && gzip -t $E/out.tar.gz && tar tzf $E/out.tar.gz | grep -q f.txt'
chk missing_src '[ "$(cat $E/m.rc)" = 1 ] && [ ! -e $E/x.tar.gz ]'
