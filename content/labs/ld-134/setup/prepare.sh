mkdir -p ~/bin
cat > ~/bin/migrate.sh <<'EOT'
#!/bin/bash
STATE="${STATE:-$HOME/state}"
mkdir -p "$STATE"
for n in 1 2 3 4; do
  if [ "$FAIL_AT" = "$n" ]; then
    echo "step $n failed" >&2
    exit 1
  fi
  echo "step$n" >> "$STATE/ledger.txt"
done
EOT
chmod +x ~/bin/migrate.sh
