chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
r=$(sysctl -n net.ipv4.ip_local_port_range)
w=$(echo "$r" | awk '{print $2-$1}')
bad=$(grep -rhE "^[[:space:]]*net.ipv4.ip_local_port_range" /etc/sysctl.d /etc/sysctl.conf 2>/dev/null | awk -F= '{split($2,a," "); if (a[2]-a[1] < 20000) n++} END{print n+0}')
chk range_wide '[ "$w" -ge 20000 ]'
chk persisted_ok '[ "$bad" = 0 ]'
chk connections_ok 'python3 - <<EOT
import socket
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(200)
port = srv.getsockname()[1]
cs = [socket.create_connection(("127.0.0.1", port)) for _ in range(100)]
EOT'
