chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
meta() { (cd "$1" && find . -printf '%p %m %T@ %y %l\n' | sort); }
chk metadata '[ -d $H/dst ] && [ "$(meta $H/src)" = "$(meta $H/dst)" ]'
chk content '[ "$(cat $H/.ex/diff.rc)" = 0 ]'
