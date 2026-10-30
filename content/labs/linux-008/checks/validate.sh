chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk dev_total '[ "$(tr -d "[:space:]" < $H/dev_total.txt)" = 18000 ]'
chk config_fixed '[ "$(cat $H/data/config.ini)" = "$(printf "debug=false\nport=8080\nname=demo")" ]'
chk names '[ "$(cat $H/names.txt)" = "$(printf "Anna\nBoris\nClara\nDenis\nElena\nFedor")" ]'
