chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
F=/home/student/diag.txt
chk bytes_ok '[ "$(grep ^bytes_full= $F | cut -d= -f2- | tr -d " ")" = /mnt/bytes ]'
chk inodes_ok '[ "$(grep ^inodes_full= $F | cut -d= -f2- | tr -d " ")" = /mnt/inodes ]'
