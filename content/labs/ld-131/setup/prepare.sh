mkdir -p ~/bin
cat > ~/bin/cleanup.sh <<'EOT'
#!/bin/bash
cd $DIR
rm -rf ./*
EOT
chmod +x ~/bin/cleanup.sh
