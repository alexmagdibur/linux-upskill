chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
probe() {
python3 - "$1" <<'EOT'
import socket, sys
try:
    s = socket.create_connection(("127.0.0.1", int(sys.argv[1])), 2)
    s.sendall(b"GET / HTTP/1.0\r\n\r\n")
    data = b""
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        data += chunk
    print("OK" if b"healthy" in data else "BAD")
except OSError:
    print("DOWN")
EOT
}
chk port_8080 '[ "$(probe 8080)" = OK ]'
chk config_port 'grep -qx "port=8080" /home/student/app/config.ini'
chk old_port_closed '[ "$(probe 9090)" = DOWN ]'
