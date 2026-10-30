mkdir -p ~/spool
cat > ~/spool/holder.py <<'EOT'
import os, signal, time
base = os.path.expanduser("~/spool")
big = open(os.path.join(base, "big.log"), "wb")
big.write(b"x" * (20 * 1024 * 1024))
big.flush()
os.unlink(os.path.join(base, "big.log"))  # файл удалён, но дескриптор открыт
def reopen(*_):
    big.close()
signal.signal(signal.SIGUSR1, reopen)
log = open(os.path.join(base, "app.log"), "a")
while True:
    log.write("tick\n"); log.flush()
    time.sleep(1)
EOT
setsid nohup python3 ~/spool/holder.py >/dev/null 2>&1 </dev/null &
sleep 1.5
