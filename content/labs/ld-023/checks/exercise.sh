mkdir -p ~/.ex; rm -f ~/.ex/partial ~/.ex/final
python3 - <<'EOT'
import os
open(os.path.expanduser("~/.ex/new.conf"), "w").write("version=2\n" + "pad=" + "x" * 3000000 + "\n")
EOT
echo "version=1" > ~/app/app.conf
[ -f ~/bin/update_config.sh ] || exit 0
( sleep 0.05; timeout 10 bash ~/bin/update_config.sh ~/.ex/new.conf > /dev/null 2>&1 < /dev/null ) &
python3 - > ~/.ex/partial <<'EOT'
import os, time
new = open(os.path.expanduser("~/.ex/new.conf"), "rb").read()
old = b"version=1\n"
bad = 0
for _ in range(400):
    data = open(os.path.expanduser("~/app/app.conf"), "rb").read()
    if data != old and data != new:
        bad += 1
    time.sleep(0.003)
print(bad)
EOT
wait
sha256sum < ~/app/app.conf > ~/.ex/final
true
