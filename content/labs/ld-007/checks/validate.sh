chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex; D=/home/student/dirs
chk function_defined 'grep -q "godir" /home/student/lib/safe.sh'
chk all_names_safe '[ "$(cat $E/g1)" = "$D/my dir" ] && [ "$(cat $E/g2)" = "$D/a*b" ] && [ "$(cat $E/g3)" = "$D/-dash" ] && [ "$(cat $E/g4)" = "$D/plain" ]'
