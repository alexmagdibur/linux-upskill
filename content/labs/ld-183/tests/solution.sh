cd ~/ansible
sed -i 's#http://127.0.0.1:81{{ node_id }}/health#http://127.0.0.1:810{{ node_id }}/health#' update.yml
ansible-playbook -i nodes.ini update.yml
