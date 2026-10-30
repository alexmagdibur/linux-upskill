sudo sh -c 'nft list ruleset > /etc/lab/rollback.nft'
sudo sed -i 's/acept/accept/' /etc/lab/new.nft
sudo nft -c -f /etc/lab/new.nft
sudo nft -f /etc/lab/new.nft
