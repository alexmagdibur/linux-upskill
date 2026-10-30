cat > ~/bin/rollout.sh <<'EOT'
#!/bin/bash
new="$1"
FLEET="${FLEET:-$HOME/fleet/hosts}"
[ -f "$new" ] || { echo "config not found" >&2; exit 2; }
hosts=$(ls "$FLEET")
echo "plan: $hosts"
if ! ~/bin/validate_conf.sh "$new"; then
  echo "invalid config, nothing changed" >&2
  exit 1
fi
changed=()
rollback() {
  for h in "${changed[@]}"; do
    cp -p "$FLEET/$h/app.conf.bak" "$FLEET/$h/app.conf" && rm -f "$FLEET/$h/app.conf.bak"
  done
}
for h in $hosts; do
  cp -p "$FLEET/$h/app.conf" "$FLEET/$h/app.conf.bak"
  changed+=("$h")
  cp "$new" "$FLEET/$h/app.conf"
  if ! ~/bin/validate_conf.sh "$FLEET/$h/app.conf" || ! ~/bin/healthcheck.sh "$FLEET/$h"; then
    echo "host $h failed, rolling back" >&2
    rollback
    exit 1
  fi
done
rm -f "$FLEET"/*/app.conf.bak
EOT
