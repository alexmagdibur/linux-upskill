install -d /opt/lab /var/lib/lab
cat > /opt/lab/flaky.py <<'EOT'
import os, sys, time
p = "/var/lib/lab/flaky.count"
n = int(open(p).read()) if os.path.exists(p) else 0
open(p, "w").write(str(n + 1))
if n < 2:
    print("flaky: crash #%d" % (n + 1), file=sys.stderr)
    sys.exit(1)
while True:
    time.sleep(5)
EOT
printf 'import sys\nprint("broken: permanent failure", file=sys.stderr)\nsys.exit(1)\n' > /opt/lab/broken.py
for n in flaky broken; do
cat > /etc/systemd/system/$n.service <<EOT
[Unit]
Description=Lab $n

[Service]
ExecStart=/usr/bin/python3 /opt/lab/$n.py
EOT
done
systemctl daemon-reload
