ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q
for u in jump inner; do
  sudo install -d -m 700 -o $u -g $u /home/$u/.ssh
  sudo install -m 600 -o $u -g $u ~/.ssh/id_ed25519.pub /home/$u/.ssh/authorized_keys
done
{ ssh-keyscan -t ed25519 10.95.1.1 2>/dev/null; ssh-keyscan -t ed25519 10.95.2.2 2>/dev/null; } >> ~/.ssh/known_hosts
cat > ~/.ssh/config <<'EOT'
Host inner
    HostName 10.95.2.2
    User inner
    ProxyJump jump@10.95.1.1
EOT
chmod 600 ~/.ssh/config
