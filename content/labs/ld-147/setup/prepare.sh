install -d /opt/lab
cat > /opt/lab/hog.py <<'EOT'
import time
chunks = []
while True:
    if len(chunks) < 30:
        chunks.append(bytearray(1024 * 1024))   # до 30 МБ малыми порциями (лимит группы 50 МБ)
    x = 0
    for i in range(200000):
        x += i
    time.sleep(0.01)
EOT
