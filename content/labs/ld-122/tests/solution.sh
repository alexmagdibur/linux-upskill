sudo mkdir -p /etc/apt/keyrings
sudo gpg --dearmor -o /etc/apt/keyrings/labrepo.gpg /srv/repo/key.asc
echo 'deb [signed-by=/etc/apt/keyrings/labrepo.gpg] file:/srv/repo ./' | sudo tee /etc/apt/sources.list.d/labrepo.list > /dev/null
sudo apt-get update -qq
sudo apt-get install -y labtool
