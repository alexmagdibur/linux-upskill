H=/home/student/lab
if [ -f "$H/answer.txt" ] && [ "$(tr -d ' \r\n' < "$H/answer.txt")" = "$H/src/app" ]; then echo "PASS answer_path"; else echo "FAIL answer_path"; fi
if [ -d "$H/notes" ]; then echo "PASS notes_dir"; else echo "FAIL notes_dir"; fi
