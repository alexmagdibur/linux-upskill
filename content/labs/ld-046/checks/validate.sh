chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
for i in $(seq 1 14); do [ -e /run/labslow.done ] && break; sleep 1; done
u=$(systemctl show -p UserspaceTimestampMonotonic --value); f=$(systemctl show -p FinishTimestampMonotonic --value)
t=$(( (f - u) / 1000000 ))
chk boot_fast '[ "$t" -lt 14 ]'
chk function_kept '[ -e /run/labslow.done ]'
