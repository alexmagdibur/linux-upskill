mkdir -p ~/work/proj ~/work/other
echo keep > ~/work/other/keep.txt
( cd ~/work/other && setsid nohup sleep 3601 ) >/dev/null 2>&1 </dev/null &
sleep 0.3
