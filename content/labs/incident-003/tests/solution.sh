sed -i 's/port=9090/port=8080/' ~/app/config.ini
pkill -f app/server.py
sleep 0.5
setsid nohup python3 ~/app/server.py >/dev/null 2>&1 </dev/null &
sleep 1
