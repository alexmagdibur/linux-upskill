timeout 3 sudo strace -p $(systemctl show -p MainPID --value labhang) -o /tmp/st.out || true
cat /tmp/st.out | head -3
echo openat > ~/syscall.txt
echo go > /run/lab/jobs.fifo
sleep 1
