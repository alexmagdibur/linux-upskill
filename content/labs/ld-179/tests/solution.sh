mkdir -p ~/ansible/templates
echo 'port={{ app_port }}' > ~/ansible/templates/app.conf.j2
cat > ~/ansible/app.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  vars:
    app_port: 8071
  tasks:
    - name: config
      ansible.builtin.template:
        src: templates/app.conf.j2
        dest: /etc/labsvc2/app.conf
        mode: "0644"
      notify: restart labsvc2
  handlers:
    - name: restart labsvc2
      ansible.builtin.systemd:
        name: labsvc2
        state: restarted
EOT
