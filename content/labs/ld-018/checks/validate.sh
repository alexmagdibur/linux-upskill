chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
L=/home/student/links
ref=$(cat /home/student/.ref_inode)
chk hard_survives '[ ! -e $L/orig.txt ] && [ "$(stat -c %i $L/hard)" = "$ref" ] && [ "$(cat $L/hard)" = data ]'
chk soft_dangles '[ -L $L/soft ] && [ ! -e $L/soft ] && [ "$(readlink $L/soft)" = orig.txt ]'
chk report 'grep -q "$ref" $L/report.txt && grep -qi hard $L/report.txt && grep -qi soft $L/report.txt'
