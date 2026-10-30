install -d /var/lib/lab
cat > /etc/systemd/system/labcrash.service <<'EOT'
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo "CRASH: code=$(cat /var/lib/lab/code)" >&2; exit 1'
EOT
systemctl daemon-reload
echo 11 > /var/lib/lab/code; systemctl start labcrash.service 2>/dev/null || true
sleep 2
date +%Y-%m-%dT%H:%M:%S > /home/student/cutoff.txt
chown student:student /home/student/cutoff.txt
sleep 1.2
echo 42 > /var/lib/lab/code; systemctl start labcrash.service 2>/dev/null || true
sleep 1
echo 77 > /var/lib/lab/code; systemctl start labcrash.service 2>/dev/null || true
