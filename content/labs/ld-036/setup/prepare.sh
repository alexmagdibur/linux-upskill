mkdir -p ~/sup
cat > ~/sup/supervisor.py <<'EOT'
import subprocess, time
for _ in range(20):
    subprocess.Popen(["/bin/true"])  # статус ребёнка никто не забирает
    time.sleep(0.15)
while True:
    time.sleep(1)
EOT
setsid nohup python3 ~/sup/supervisor.py >/dev/null 2>&1 </dev/null &
sleep 3.8
