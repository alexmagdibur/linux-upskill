install -d /opt/lab /var/lib/labapp /var/backups/labapp
cat > /opt/lab/writer.py <<'EOT'
import sqlite3, time
db = sqlite3.connect("/var/lib/labapp/orders.db", isolation_level=None)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, ts REAL, note TEXT)")
while True:
    db.execute("INSERT INTO orders (ts, note) VALUES (?, ?)", (time.time(), "x" * 200))
    time.sleep(0.02)
EOT
cat > /etc/systemd/system/labdb-writer.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/writer.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labdb-writer >/dev/null 2>&1
sleep 2
