sudo tee /usr/local/bin/lab-alert > /dev/null <<'EOT'
#!/usr/bin/env python3
import math, sys

log, now = sys.argv[1], int(sys.argv[2])
rows = []
for line in open(log):
    parts = line.split()
    if len(parts) != 3:
        continue
    ts, status, lat = int(parts[0]), int(parts[1]), float(parts[2])
    if now - 300 < ts <= now:
        rows.append((status, lat))
n = len(rows)
if n < 20:
    print("OK insufficient-data")
    sys.exit(0)
errors = sum(1 for s, _ in rows if s >= 500) / n
lats = sorted(l for _, l in rows)
p95 = lats[math.ceil(0.95 * n) - 1]
if errors >= 0.05:
    print("ALERT error-rate=%.3f" % errors)
elif p95 > 500:
    print("ALERT p95=%d" % p95)
else:
    print("OK")
EOT
sudo chmod 755 /usr/local/bin/lab-alert
