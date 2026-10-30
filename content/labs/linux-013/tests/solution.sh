pgrep -f bin/worker.sh > ~/found_pid.txt
pkill -9 -f bin/stuck.sh
sleep 0.3
