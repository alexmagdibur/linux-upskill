cat > ~/backup.sh <<'EOT'
#!/bin/bash
src="$1"; dest="$2"
if [ ! -d "$src" ]; then
  echo "error: source directory not found: $src" >&2
  exit 1
fi
mkdir -p "$dest"
out="$dest/backup-$(date +%F).tar.gz"
tar czf "$out" -C "$src" . && echo "Backup created: $out"
EOT
