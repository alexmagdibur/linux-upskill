chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk option_named 'grep -q -- "-S" $H/option.txt && grep -qiE "size|размер" $H/option.txt'
chk sorted_by_size '[ "$(cat $H/sorted.txt)" = "$(printf "big.dat\nmid.dat\nsmall.dat\ntiny.dat")" ]'
