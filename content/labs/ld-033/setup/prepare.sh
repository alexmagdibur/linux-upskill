mkdir -p ~/srv
cat > ~/srv/svc.py <<'EOT'
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1])))
s.listen(5)
while True:
    time.sleep(60)
EOT
for p in 9101 9102 9103; do setsid nohup python3 ~/srv/svc.py $p >/dev/null 2>&1 </dev/null & done
sleep 1
