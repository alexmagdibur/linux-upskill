chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk job_runs '[ "$(cat /home/student/.ex/out)" = "job done" ]'
chk tmp_untouched '[ "$(stat -c %a /tmp/job/data.txt)" = 644 ] && { [ ! -e /tmp/job/run.sh ] || [ "$(stat -c %a /tmp/job/run.sh)" = 755 ]; }'
