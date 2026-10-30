chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk visible '[ "$(sort $H/visible.txt)" = "$(printf "a.txt\nb.txt\ndocs\nnotes.md")" ]'
chk hidden '[ "$(sort $H/hidden.txt)" = "$(printf ".cache\n.env\n.secret")" ]'
