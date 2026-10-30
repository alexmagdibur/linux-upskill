cat > ~/bin/report.py <<'EOT'
import collections, json, sys

log, out = sys.argv[1], sys.argv[2]
w = open(out, "w")
counts = collections.Counter()
for line in open(log):
    if "CORRUPT" in line:
        sys.exit(2)
    i = line.find("status=")
    if i >= 0:
        counts[line[i + 7:i + 10]] += 1
json.dump(counts, w)
w.close()
EOT
