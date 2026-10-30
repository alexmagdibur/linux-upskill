mkdir -p ~/ansible
cat > ~/ansible/site.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: everything
      ansible.builtin.shell: |
        id labsvc || useradd -r labsvc
        echo hello > /opt/labsvc/index.html
      args:
        creates: /nonexistent
EOT
