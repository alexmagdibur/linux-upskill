chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk archive 'gzip -t $H/backup.tar.gz && tar tzf $H/backup.tar.gz | grep -q "data/secret.txt"'
chk checksum 'grep -q "$(sha256sum $H/backup.tar.gz | cut -d" " -f1)" $H/backup.sha256'
chk perms '[ "$(stat -c %a $H/restore/data/a.sh)" = 755 ] && [ "$(stat -c %a $H/restore/data/secret.txt)" = 600 ] && [ "$(stat -c %a $H/restore/data/shared.txt)" = 664 ]'
chk content '[ "$(cat $H/.ex/diff.rc)" = 0 ] && [ -L $H/restore/data/latest ] && [ "$(readlink $H/restore/data/latest)" = shared.txt ]'
