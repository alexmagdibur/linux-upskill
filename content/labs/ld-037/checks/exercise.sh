mkdir -p ~/.ex; rm -f ~/.ex/res
cd ~/svc
python3 service.py > /dev/null 2>&1 < /dev/null &
pid=$!
sleep 1
kill -TERM $pid
t0=$(date +%s.%N)
alive() { s=$(ps -o stat= -p $pid 2>/dev/null); [ -n "$s" ] && [ "${s:0:1}" != Z ]; }
for i in $(seq 1 90); do alive || break; sleep 0.1; done
t1=$(date +%s.%N)
a=0; alive && a=1
k=$(pgrep -fc 'STUCK[C]HILD' || true)
secs=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b-a}')
echo "alive=$a kids=${k:-0} secs=$secs" > ~/.ex/res
pkill -9 -f 'STUCK[C]HILD'; kill -9 $pid 2>/dev/null
true
