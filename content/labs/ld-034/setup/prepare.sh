mkdir -p ~/run
cat > ~/run/holder.py <<'EOT'
import os, signal, sys, time
fd = open(os.path.expanduser("~/run/data.lock"), "w")
def bye(*_):
    with open(os.path.expanduser("~/run/exit.log"), "w") as f:
        f.write("clean exit\n")
    sys.exit(0)
signal.signal(signal.SIGTERM, bye)
while True:
    time.sleep(1)
EOT
setsid nohup python3 ~/run/holder.py >/dev/null 2>&1 </dev/null &
sleep 0.5
