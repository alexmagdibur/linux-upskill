cat > ~/bin/report.sh <<'EOT'
#!/bin/bash
set -o pipefail
mkdir -p ~/out
if cat ~/in/input.txt | sort > ~/out/sorted.txt; then
  echo "status: OK" > ~/out/status.txt
else
  echo "status: FAILED" > ~/out/status.txt
  exit 1
fi
EOT
