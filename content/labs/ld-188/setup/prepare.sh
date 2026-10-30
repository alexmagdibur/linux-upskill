install -d /etc/lab/ca /etc/lab/tls /opt/lab
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=Lab Root CA" >/dev/null 2>&1
mk() { # имя дней
  openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/$1.key -out /tmp/$1.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
  openssl x509 -req -in /tmp/$1.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days $2 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/$1.crt >/dev/null 2>&1
}
mk new 30
# «старый» сертификат — выпущен другим CA, которому клиент не доверяет
openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/oldca.key -out /tmp/oldca.crt -days 30 -subj "/CN=Old CA" >/dev/null 2>&1
openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/old.key -out /tmp/old.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
openssl x509 -req -in /tmp/old.csr -CA /tmp/oldca.crt -CAkey /tmp/oldca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/old.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/ca.crt /etc/lab/tls/*.crt; chmod 640 /etc/lab/tls/*.key
printf 'CERT=/etc/lab/tls/new.crt\nKEY=/etc/lab/tls/new.key\n' > /etc/lab/tls/labtls-1.env
printf 'CERT=/etc/lab/tls/old.crt\nKEY=/etc/lab/tls/old.key\n' > /etc/lab/tls/labtls-2.env
cat > /opt/lab/tlsback.py <<'EOT'
import socket, ssl, sys
n = sys.argv[1]
env = dict(l.strip().split("=", 1) for l in open("/etc/lab/tls/labtls-%s.env" % n) if "=" in l)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(env["CERT"], env["KEY"])
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 9300 + int(n))); s.listen(20)
while True:
    c, _ = s.accept()
    try:
        t = ctx.wrap_socket(c, server_side=True)
        t.recv(4096)
        t.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n")
        t.close()
    except Exception:
        c.close()
EOT
cat > /etc/systemd/system/labtls@.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/tlsback.py %i
[Install]
WantedBy=multi-user.target
EOT
cat > /opt/lab/lb.py <<'EOT'
import itertools, socket, threading

backends = itertools.cycle([("127.0.0.1", 9301), ("127.0.0.1", 9302)])

def pipe(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

def handle(c):
    try:
        u = socket.create_connection(next(backends), timeout=3)
    except OSError:
        c.close()
        return
    threading.Thread(target=pipe, args=(c, u), daemon=True).start()
    threading.Thread(target=pipe, args=(u, c), daemon=True).start()

s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8443)); s.listen(50)
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
EOT
cat > /etc/systemd/system/lab-lb.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/lb.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labtls@1 labtls@2 lab-lb >/dev/null 2>&1
sleep 1
