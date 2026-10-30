cat > ~/bin/rollout.sh <<'EOT'
#!/bin/bash
for h in $(ls "${FLEET:-$HOME/fleet/hosts}"); do cp "$1" "${FLEET:-$HOME/fleet/hosts}/$h/app.conf"; done
EOT
