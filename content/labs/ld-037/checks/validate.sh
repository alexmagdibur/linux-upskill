chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
R=$(cat /home/student/.ex/res)
chk service_exits 'echo "$R" | grep -q "alive=0"'
chk no_children 'echo "$R" | grep -q "kids=0"'
chk in_deadline 'awk -v s="$(echo "$R" | sed "s/.*secs=//")" "BEGIN{exit !(s+0 <= 6.0)}"'
