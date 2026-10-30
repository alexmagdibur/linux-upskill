mkdir -p ~/ansible/templates
echo 'port={{ app_port }}' > ~/ansible/templates/app.conf.j2
cat > ~/ansible/app.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  vars:
    app_port: 8071
  tasks:
    - ansible.builtin.template:
        src: templates/app.conf.j2
        dest: /etc/labsvc2/app.conf
    - ansible.builtin.systemd:
        name: labsvc2
        state: restarted
EOT
