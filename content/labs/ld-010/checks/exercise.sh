mkdir -p ~/.ex
python3 - > ~/.ex/hidden.log <<'EOT'
import random
random.seed(7)
ips = ["10.1.1.%d" % i for i in range(1, 9)]
weights = [3, 9, 1, 7, 5, 9, 2, 5]
for _ in range(120):
    print("%s - GET /x 200" % random.choices(ips, weights)[0])
EOT
[ -f ~/ipcount.sh ] && timeout 8 bash ~/ipcount.sh ~/.ex/hidden.log > ~/.ex/out.csv 2>/dev/null < /dev/null
true
