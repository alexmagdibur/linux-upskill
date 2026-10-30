cat > ~/bin/cleanup.sh <<'EOT'
#!/bin/bash
dir="${DIR:-}"
if [ -z "$dir" ] || [ ! -d "$dir" ]; then
  echo "refusing to clean: DIR is empty or not a directory" >&2
  exit 1
fi
find "$dir" -mindepth 1 -delete
EOT
