cd ~/ansible
sudo ansible-playbook -i localhost, -c local fleet.yml --check --diff | head -20
echo n2 > ~/drift.txt
sudo ansible-playbook -i localhost, -c local fleet.yml
