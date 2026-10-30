chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
used=$(df --output=ipcent /var/lib/labapp/spool | tail -n 1 | tr -dc '0-9')
chk writer_works '[ "$(cat /tmp/.ex/writer.rc)" = 0 ] && ls /var/lib/labapp/spool/job-* >/dev/null 2>&1'
chk inode_usage_low '[ "$used" -lt 80 ]'
chk keep_intact '[ "$(cat /var/lib/labapp/spool/keep/data1 /var/lib/labapp/spool/keep/data2 /var/lib/labapp/spool/keep/data3 | wc -l)" = 3 ]'
