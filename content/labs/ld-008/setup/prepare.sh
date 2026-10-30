mkdir -p ~/bin ~/in ~/out
printf 'b\na\nc\n' > ~/in/input.txt
cat > ~/bin/report.sh <<'EOT'
#!/bin/bash
mkdir -p ~/out
cat ~/in/input.txt | sort > ~/out/sorted.txt
echo "status: OK" > ~/out/status.txt
EOT
chmod +x ~/bin/report.sh
