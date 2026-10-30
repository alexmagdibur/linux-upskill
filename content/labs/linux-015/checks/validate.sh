chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
E=$H/.ex
F=$H/backups/backup-$(date +%F).tar.gz
chk script_exists '[ -f $H/backup.sh ]'
chk backup_created '[ -f $F ]'
chk archive_valid 'gzip -t $F && L=$(tar tzf $F) && echo "$L" | grep -q report.txt && echo "$L" | grep -q notes.md'
chk exit_code_ok '[ "$(cat $E/rc1.txt)" = 0 ] && grep -q "Backup created" $E/out1.txt'
chk missing_source '[ -n "$(cat $E/rc2.txt)" ] && [ "$(cat $E/rc2.txt)" != 0 ] && [ ! -e $H/backups2 ]'
