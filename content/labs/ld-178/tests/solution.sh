mkdir -p ~/ansible
cat > ~/ansible/site.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: service user
      ansible.builtin.user:
        name: labsvc
        system: true
        shell: /usr/sbin/nologin
        create_home: false
    - name: app dir
      ansible.builtin.file:
        path: /opt/labsvc
        state: directory
        owner: labsvc
        mode: "0755"
    - name: index
      ansible.builtin.copy:
        content: "hello\n"
        dest: /opt/labsvc/index.html
        owner: labsvc
        mode: "0644"
    - name: unit
      ansible.builtin.copy:
        dest: /etc/systemd/system/labsvc.service
        content: |
          [Service]
          User=labsvc
          WorkingDirectory=/opt/labsvc
          ExecStart=/usr/bin/python3 -m http.server 8070 --bind 127.0.0.1
          [Install]
          WantedBy=multi-user.target
    - name: service
      ansible.builtin.systemd:
        name: labsvc
        daemon_reload: true
        enabled: true
        state: started
EOT
