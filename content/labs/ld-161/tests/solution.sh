python3 - <<'EOT'
import re, subprocess
allowed = {l.strip() for l in open("/etc/lab/allowed-ports") if l.strip()}
out = subprocess.run(["sudo", "ss", "-ltnpH"], capture_output=True, text=True).stdout
lines = []
for line in out.splitlines():
    cols = line.split()
    host, _, port = cols[3].rpartition(":")
    if host.startswith("127.") or host.strip("[]") == "::1" or port in allowed:
        continue
    m = re.search(r'\("([^"]+)",pid=(\d+)', line)
    lines.append("%s %s %s" % (port, m.group(2), m.group(1)))
open("/home/student/unexpected.txt", "w").write("\n".join(lines) + "\n")
EOT
