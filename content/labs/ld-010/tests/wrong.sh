cat > ~/ipcount.sh <<'EOT'
#!/bin/bash
echo "ip,count"
awk '{print $1}' "$1" | sort | uniq -c | awk '{print $2 "," $1}'
EOT
