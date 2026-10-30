mkdir -p ~/bin ~/data ~/out
printf 'Ёлка\nÄrger\nplain\nZebra\n' > ~/data/names.txt
cat > ~/bin/report.sh <<'EOT'
#!/bin/bash
mkdir -p ~/out
awk '{ print $1, length($1) }' ~/data/names.txt | sort
EOT
chmod +x ~/bin/report.sh
