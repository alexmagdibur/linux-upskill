chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
W=/home/student/workspace
chk project_todo '[ -d $W/project ] && [ -f $W/project/todo.txt ] && [ ! -s $W/project/todo.txt ]'
chk backup_copy '[ "$(cat $W/keep.txt)" = "important data" ] && [ "$(cat $W/project/keep_backup.txt)" = "important data" ]'
chk logs_removed '[ ! -e $W/tmp1.log ] && [ ! -e $W/tmp2.log ] && [ -f $W/keep.txt ]'
chk renamed '[ "$(cat $W/notes.txt)" = draft ] && [ ! -e $W/old_notes.txt ]'
