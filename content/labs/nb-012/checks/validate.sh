chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk codes '[ "$(sed -n 1p $H/codes.txt)" = ok=0 ] && [ "$(sed -n 2p $H/codes.txt)" = fail=2 ]'
chk why 'grep -qiE "no such file|не существует|нет такого" $H/why.txt'
