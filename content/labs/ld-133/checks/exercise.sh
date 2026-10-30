mkdir -p ~/.ex; rm -f ~/.ex/small.out ~/.ex/large.out
[ -f ~/bin/parse.py ] || exit 0
cat > ~/.ex/small.jsonl <<'EOT'
{"user":"alice","amount":10.5,"status":"ok"}
{"user":"bob","amount":3,"status":"ok"}
not json at all
{"user":"alice","amount":4.25,"status":"fail"}
{"user":"юзер","amount":1.1,"status":"ok"}
{"user":"bob","amount":2.2,"status":"ok"}
{"amount":5,"status":"ok"}
EOT
timeout 8 python3 ~/bin/parse.py < ~/.ex/small.jsonl > ~/.ex/small.out 2>/dev/null
python3 - <<'EOT' | ( ulimit -v 130000; timeout 12 python3 ~/bin/parse.py > ~/.ex/large.out 2>/dev/null )
import sys
w = sys.stdout.write
for i in range(600000):
    w('{"user":"u%d","amount":%s,"status":"%s"}\n' % (i % 10, (i % 7) + 0.5, "ok" if i % 3 else "fail"))
EOT
true
