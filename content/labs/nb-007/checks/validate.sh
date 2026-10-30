chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
N=/home/student/notes
chk empty_file '[ -f $N/notes.txt ] && [ ! -s $N/notes.txt ]'
chk message '[ "$(cat $N/message.txt)" = "Hello, Linux!" ]'
