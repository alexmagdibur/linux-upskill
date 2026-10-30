mkdir -p ~/probe_dir
cat > ~/probe.py <<'EOT'
import os, time
os.chdir(os.path.expanduser("~/probe_dir"))
held = open("held.txt", "w")
while True:
    time.sleep(1)
EOT
PROBE_TOKEN=xyz123 setsid nohup python3 ~/probe.py >/dev/null 2>&1 </dev/null &
sleep 0.7
