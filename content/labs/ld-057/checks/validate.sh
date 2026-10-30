chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
F=/home/student/first_failure.txt
boot=$(tr -d "-" < /proc/sys/kernel/random/boot_id)
chk unit_ok 'grep -qx "unit=labcrash.service" $F'
chk message_ok '[ "$(grep ^message= $F | cut -d= -f2-)" = "CRASH: code=42" ]'
chk boot_ok '[ "$(grep ^boot= $F | cut -d= -f2- | tr -d "-")" = "$boot" ]'
