sudo apt-get install -y --allow-downgrades labfmt=1.0
sudo apt-mark hold labfmt
sudo systemctl restart labapp
sleep 3
