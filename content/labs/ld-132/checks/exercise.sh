mkdir -p ~/.ex; rm -f ~/.ex/counter ~/.ex/c1 ~/.ex/c2 ~/.job.lock; rm -rf ~/.job.lock.d ~/.job.lockdir
[ -f ~/bin/job_locked.sh ] || exit 0
export COUNTER=$HOME/.ex/counter
setsid bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null &
setsid bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null &
sleep 3.5
( [ -f ~/.ex/counter ] && wc -l < ~/.ex/counter || echo 0 ) > ~/.ex/c1
setsid bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null &
jp=$!
sleep 0.6
kill -TERM -- -$jp 2>/dev/null
sleep 0.4
timeout 6 bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null
( [ -f ~/.ex/counter ] && wc -l < ~/.ex/counter || echo 0 ) > ~/.ex/c2
true
