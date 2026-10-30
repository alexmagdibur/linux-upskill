chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
sleep 4
chk no_zombies '[ "$(ps -eo stat= | grep -c "^Z")" = 0 ]'
chk supervisor_alive 'pgrep -f "sup/supervisor.py"'
