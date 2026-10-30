mkdir -p ~/app/logs
cat > ~/app/app.py <<'EOT'
import datetime, os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "app.log")
with open(path, "a") as f:
    f.write("%s started OK\n" % datetime.datetime.now().isoformat())
EOT
cat > ~/app/start.sh <<'EOT'
#!/bin/bash
cd "$(dirname "$0")" || exit 1
exec python3 app.py
EOT
chmod 644 ~/app/start.sh
chmod 555 ~/app/logs
