sudo tee /usr/local/bin/lab-alert > /dev/null <<'EOT'
#!/bin/bash
if grep -q ' 500 ' "$1"; then echo ALERT; else echo OK; fi
EOT
sudo chmod 755 /usr/local/bin/lab-alert
