install -d /opt/lab /var/lib/lab
dd if=/dev/urandom of=/var/lib/lab/cache.bin bs=1M count=40 2>/dev/null
cat > /opt/lab/mem.py <<'EOT'
import mmap, time

data = bytearray(b"x") * (60 * 1024 * 1024)      # 60 МБ реально занятой памяти (RSS)
reserve = mmap.mmap(-1, 300 * 1024 * 1024)        # 300 МБ адресного пространства без обращения (только VSZ)
with open("/var/lib/lab/cache.bin", "rb") as f:    # читаем файл целиком: страницы остаются в page cache
    while f.read(1 << 20):
        pass
while True:
    time.sleep(1)
EOT
cat > /etc/systemd/system/labmem.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/mem.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labmem.service >/dev/null 2>&1
sleep 3
