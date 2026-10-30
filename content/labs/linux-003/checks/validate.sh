chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
D=/home/student/data
chk last5 '[ "$(cat $D/last5.txt)" = "$(seq -f "event %g ok" 96 100)" ]'
chk first3 '[ "$(cat $D/first3.txt)" = "$(printf "alice\nbob\ncarol")" ]'
chk count 'grep -qE "^[[:space:]]*100([[:space:]]|$)" $D/count.txt'
