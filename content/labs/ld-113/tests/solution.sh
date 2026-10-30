ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q
sudo install -d -m 700 -o labuser -g labuser /home/labuser/.ssh
sudo install -m 600 -o labuser -g labuser ~/.ssh/id_ed25519.pub /home/labuser/.ssh/authorized_keys
ssh-keyscan -t ed25519 127.0.0.1 2>/dev/null > /tmp/hk
ssh-keygen -lf /tmp/hk
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
cat /tmp/hk >> ~/.ssh/known_hosts
