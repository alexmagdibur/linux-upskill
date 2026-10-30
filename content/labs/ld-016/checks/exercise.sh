rm -rf ~/.ex; mkdir -p ~/.ex/rep
[ -f ~/bin/report.py ] || exit 0
python3 - > ~/.ex/rep/big.log <<'EOT'
import sys
w = sys.stdout.write
codes = [200, 200, 200, 404, 500]
for i in range(300000):
    w("10.0.0.%d GET /p status=%d\n" % (i % 250, codes[i % 5]))
EOT
( ulimit -v 130000; timeout 12 python3 ~/bin/report.py ~/.ex/rep/big.log ~/.ex/rep/out.json > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc_ok )
printf '10.0.0.1 GET / status=200\n10.0.0.2 CORRUPT line\n10.0.0.3 GET / status=200\n' > ~/.ex/rep/bad.log
echo OLD > ~/.ex/rep/out2.json
timeout 8 python3 ~/bin/report.py ~/.ex/rep/bad.log ~/.ex/rep/out2.json > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc_bad
ls -A ~/.ex/rep > ~/.ex/listing
true
