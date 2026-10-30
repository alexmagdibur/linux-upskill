chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk found '[ "$(sort /home/student/found.txt)" = "/home/student/tree/data/big_recent.bin" ]'
