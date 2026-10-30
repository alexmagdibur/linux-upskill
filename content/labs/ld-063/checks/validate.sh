chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
: > /var/log/lab/app.log; : > /var/log/lab/worker.log
curl -s -m 4 http://127.0.0.1:8090/order >/dev/null
sleep 2
rid=$(tail -n 1 /var/log/nginx/trace.log 2>/dev/null | grep -o "rid=[0-9a-f]\{16,\}" | cut -d= -f2)
chk nginx_logs_rid '[ -n "$rid" ]'
chk app_sees_rid '[ -n "$rid" ] && grep -q "rid=$rid" /var/log/lab/app.log'
chk worker_sees_rid '[ -n "$rid" ] && grep -q "rid=$rid" /var/log/lab/worker.log'
