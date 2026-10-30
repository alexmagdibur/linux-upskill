python3 - <<'EOT'
import csv
with open("/home/student/data/events.csv", newline="") as src, open("/home/student/errors.csv", "w", newline="") as dst:
    r, w = csv.reader(src), csv.writer(dst)
    header = next(r)
    w.writerow(header)
    for row in r:
        if row[2] == "ERROR":
            w.writerow(row)
EOT
