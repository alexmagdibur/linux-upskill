printf 'Package: labcore\nPin: version 1.0\nPin-Priority: 1001\n' | sudo tee /etc/apt/preferences.d/labcore > /dev/null
sudo apt-get install -y labcore
