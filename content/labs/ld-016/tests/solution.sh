cat > ~/bin/report.py <<'EOT'
import collections, json, os, sys

log, out = sys.argv[1], sys.argv[2]
tmp = out + ".tmp"
try:
    counts = collections.Counter()
    with open(log) as f:
        for line in f:
            if "CORRUPT" in line:
                raise ValueError("corrupt line")
            i = line.find("status=")
            if i >= 0:
                counts[line[i + 7:i + 10]] += 1
    with open(tmp, "w") as w:
        json.dump(counts, w)
        w.flush()
        os.fsync(w.fileno())
    os.replace(tmp, out)
except Exception as exc:
    if os.path.exists(tmp):
        os.unlink(tmp)
    print("error:", exc, file=sys.stderr)
    sys.exit(2)
EOT
