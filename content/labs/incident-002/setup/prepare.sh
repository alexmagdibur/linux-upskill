echo "MARKER current-log-keep-me" > /var/log/app/app.log
dd if=/dev/zero of=/var/log/app/app.log.1 bs=1M count=3 2>/dev/null
dd if=/dev/zero of=/var/log/app/app.log.2 bs=1M count=3 2>/dev/null
dd if=/dev/zero of=/var/log/app/app.log.3 bs=1M 2>/dev/null
mkdir -p ~/bin
cat > ~/bin/app.sh <<'EOT'
#!/bin/bash
echo "$(date +%T) service ok" >> /var/log/app/app.log || { echo "ERROR: cannot write log" >&2; exit 1; }
EOT
chmod +x ~/bin/app.sh
true
