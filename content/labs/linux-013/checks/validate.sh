chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
wp=$(pgrep -f 'bin/worker.sh' | head -n 1)
chk worker_alive '[ -n "$wp" ]'
chk pid_found '[ -n "$wp" ] && [ "$(tr -d "[:space:]" < /home/student/found_pid.txt)" = "$wp" ]'
chk stuck_stopped '! pgrep -f "bin/stuck.sh" > /dev/null'
