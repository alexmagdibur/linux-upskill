install -d -o student -g student /home/student/ansible /home/student/ansible/templates
install -d /etc/lab
cat > /home/student/ansible/templates/node.conf.j2 <<'EOT'
node={{ item }}
worker_threads=8
log_level=info
EOT
cat > /home/student/ansible/fleet.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: node config
      ansible.builtin.template:
        src: templates/node.conf.j2
        dest: "/etc/lab/{{ item }}.conf"
        mode: "0644"
      loop: [n1, n2, n3]
EOT
chown -R student:student /home/student/ansible
cd /home/student/ansible && ansible-playbook -i localhost, -c local fleet.yml >/dev/null 2>&1
sed -i 's/worker_threads=8/worker_threads=2/' /etc/lab/n2.conf
sha256sum /home/student/ansible/fleet.yml /home/student/ansible/templates/node.conf.j2 > /root/.fleet.ref
