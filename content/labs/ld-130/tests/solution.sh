cat > ~/bin/provision.sh <<'EOT'
#!/bin/bash
mkdir -p ~/srv/app
grep -qx 'port=8080' ~/srv/app/app.conf 2>/dev/null || echo 'port=8080' >> ~/srv/app/app.conf
for u in alice bob; do
  grep -qx "$u" ~/srv/app/users.txt 2>/dev/null || echo "$u" >> ~/srv/app/users.txt
done
EOT
