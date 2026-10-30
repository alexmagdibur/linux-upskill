cat > ~/bin/provision.sh <<'EOT'
#!/bin/bash
mkdir -p ~/srv/app
echo 'port=8080' >> ~/srv/app/app.conf
echo alice >> ~/srv/app/users.txt
echo bob >> ~/srv/app/users.txt
EOT
