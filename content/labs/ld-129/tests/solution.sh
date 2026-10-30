cat > ~/bin/arch.sh <<'EOT'
#!/bin/bash
usage() { echo "Usage: arch.sh SRC_DIR DEST.tar.gz"; }
if [ "$1" = "-h" ]; then usage; exit 0; fi
if [ $# -ne 2 ]; then usage >&2; exit 2; fi
src="$1"; dest="$2"
if [ ! -d "$src" ]; then echo "error: no such directory: $src" >&2; exit 1; fi
tar czf "$dest" -C "$src" .
EOT
