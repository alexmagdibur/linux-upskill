chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
F=/home/student/unexpected.txt
expected() { python3 - <<'EOT'
import re, subprocess
allowed = {l.strip() for l in open("/etc/lab/allowed-ports") if l.strip()}
out = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout
res = {}
for line in out.splitlines():
    cols = line.split()
    addr = cols[3]
    host, _, port = addr.rpartition(":")
    if host.strip("[]") in ("127.0.0.1", "::1") or host.startswith("127."):
        continue
    if port in allowed:
        continue
    m = re.search(r"pid=(\d+)", line)
    res[port] = m.group(1) if m else "?"
for p in sorted(res):
    print(p, res[p])
EOT
}
got() { awk 'NF>=2{print $1, $2}' $F | sort; }
want=$(expected | sort)
chk ports_exact '[ -n "$want" ] && [ "$(echo "$want" | cut -d" " -f1)" = "$(got | cut -d" " -f1)" ]'
chk pids_exact '[ -n "$want" ] && [ "$want" = "$(got)" ]'
chk services_alive 'systemctl is-active --quiet miner && systemctl is-active --quiet debugd'
