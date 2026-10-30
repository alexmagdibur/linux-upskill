chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk uses_system_python 'grep -q "^OK python 3" $H/.ex/out'
chk both_available '[ -x $H/opt/old/python3 ] && [ -x /usr/bin/python3 ]'
