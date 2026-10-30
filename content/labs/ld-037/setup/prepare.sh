mkdir -p ~/svc
cat > ~/svc/service.py <<'EOT'
import signal, subprocess, sys, time

child = subprocess.Popen([sys.executable, "-c",
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(3600)  # STUCKCHILD"])

def on_term(*_):
    child.wait()      # ждём вечно: ребёнок игнорирует SIGTERM
    sys.exit(0)

signal.signal(signal.SIGTERM, on_term)
while True:
    time.sleep(0.5)
EOT
