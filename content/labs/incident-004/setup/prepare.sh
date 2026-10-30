printf 'MODE=production\nLEVEL=info\n' > /etc/myapp/app.conf
mkdir -p ~/app
cat > ~/app/run.sh <<'EOT'
#!/bin/bash
CONF="${APP_CONFIG:-/etc/myapp/application.conf}"
if [ ! -r "$CONF" ]; then
  echo "FATAL: config not found: $CONF" >&2
  exit 2
fi
. "$CONF"
echo "app started mode=$MODE" >> "$HOME/app/app.log"
EOT
chmod +x ~/app/run.sh
