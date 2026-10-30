cat > ~/bin/update_config.sh <<'EOT'
#!/bin/bash
set -e
new="$1"
dst="$HOME/app/app.conf"
tmp="$(mktemp "$(dirname "$dst")/.app.conf.XXXXXX")"
cp "$new" "$tmp"
chmod 644 "$tmp"
sync "$tmp" 2>/dev/null || sync
mv -f "$tmp" "$dst"
EOT
chmod +x ~/bin/update_config.sh
