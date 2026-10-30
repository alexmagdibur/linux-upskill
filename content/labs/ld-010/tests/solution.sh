cat > ~/ipcount.sh <<'EOT'
#!/bin/bash
echo "ip,count"
awk '{print $1}' "$1" | sort | uniq -c | sort -k1,1nr -k2,2 | awk '{print $2 "," $1}'
EOT
