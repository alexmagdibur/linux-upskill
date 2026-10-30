echo n1 > ~/drift.txt
sudo sed -i 's/worker_threads=2/worker_threads=8/' /etc/lab/n2.conf
sed -i 's/worker_threads=8/worker_threads=2/' ~/ansible/templates/node.conf.j2
