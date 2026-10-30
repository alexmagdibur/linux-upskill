cat > ~/bin/migrate.sh <<'EOT'
#!/bin/bash
STATE="${STATE:-$HOME/state}"
mkdir -p "$STATE"
for n in 1 2 3 4; do
  grep -qx "step$n" "$STATE/done" 2>/dev/null && continue
  if [ "$FAIL_AT" = "$n" ]; then
    echo "step $n failed" >&2
    exit 1
  fi
  echo "step$n" >> "$STATE/ledger.txt"
  echo "step$n" >> "$STATE/done"
done
EOT
