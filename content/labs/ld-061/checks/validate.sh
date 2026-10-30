chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
D=/var/log/lab
s1=$(stat -c %s $D/app.log 2>/dev/null || echo 0); sleep 1; s2=$(stat -c %s $D/app.log 2>/dev/null || echo 0)
cont() { python3 - <<'EOT'
import glob, re
nums = set()
for p in glob.glob("/var/log/lab/app.log*"):
    for line in open(p, errors="replace"):
        m = re.fullmatch(r"line (\d+)\n", line)
        if m:
            nums.add(int(m.group(1)))
print("OK" if nums and max(nums) - min(nums) + 1 == len(nums) else "BAD")
EOT
}
chk rotated '[ -f $D/app.log.1 ]'
chk new_log_grows '[ "$s2" -gt "$s1" ]'
chk no_lost_lines '[ "$(cont)" = OK ]'
