echo 'deb [trusted=yes] file:/srv/repo ./' | sudo tee /etc/apt/sources.list.d/labrepo.list > /dev/null
sudo apt-get update -qq
sudo apt-get install -y labtool
