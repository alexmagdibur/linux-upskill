chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk process_gone '! pgrep -f "run/holder.py"'
chk clean_exit 'grep -qx "clean exit" /home/student/run/exit.log'
