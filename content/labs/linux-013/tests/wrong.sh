pgrep -f bin/stuck.sh > ~/found_pid.txt
pkill -f bin/stuck.sh
pkill -9 -f bin/worker.sh
sleep 0.3
