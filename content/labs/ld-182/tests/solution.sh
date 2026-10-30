cat > ~/ansible/rolling.yml <<'EOT'
- hosts: nodes
  serial: 1
  gather_facts: false
  vars:
    new_version: v2
  tasks:
    - name: version
      ansible.builtin.copy:
        content: "{{ new_version }}\n"
        dest: "/etc/labnode/{{ node_id }}.version"
    - name: restart
      ansible.builtin.systemd:
        name: "labnode@{{ node_id }}"
        state: restarted
    - name: health gate
      ansible.builtin.uri:
        url: "http://127.0.0.1:810{{ node_id }}/health"
        status_code: 200
      register: h
      until: h.status == 200
      retries: 20
      delay: 1
EOT
