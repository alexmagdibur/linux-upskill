chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
expected() { python3 - <<'EOT'
import collections
c = collections.Counter(l.split()[0] for l in open("/home/student/.ex/hidden.log"))
print("ip,count")
for ip, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
    print("%s,%d" % (ip, n))
EOT
}
chk csv '[ "$(cat /home/student/.ex/out.csv)" = "$(expected)" ]'
