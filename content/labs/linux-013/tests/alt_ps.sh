ps -eo pid,args | awk '/bin\/worker.sh/ && !/awk/ {print $1}' > ~/found_pid.txt
kill -KILL $(pgrep -f bin/stuck.sh)
sleep 0.3
