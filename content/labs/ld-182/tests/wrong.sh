cat > ~/ansible/rolling.yml <<'EOT'
- hosts: nodes
  gather_facts: false
  tasks:
    - ansible.builtin.copy:
        content: "v2\n"
        dest: "/etc/labnode/{{ node_id }}.version"
    - ansible.builtin.systemd:
        name: "labnode@{{ node_id }}"
        state: restarted
EOT
