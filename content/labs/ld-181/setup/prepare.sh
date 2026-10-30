install -d -o student -g student /home/student/ansible/vars
install -d /etc/lab
cat > /home/student/ansible/vars/all.yml <<'EOT'
db_host: db.lab.test
db_password: S3cretPass
EOT
cat > /home/student/ansible/db.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  vars_files:
    - vars/all.yml
  tasks:
    - name: db config
      ansible.builtin.copy:
        dest: /etc/lab/db.conf
        content: |
          host={{ db_host }}
          password={{ db_password }}
        mode: "0600"
EOT
chown -R student:student /home/student/ansible
