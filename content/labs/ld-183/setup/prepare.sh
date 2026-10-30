install -d /opt/lab /etc/labnode /var/lib/lab
cat > /opt/lab/labnode.py <<'EOT'
import http.server, socketserver, sys, time
n = sys.argv[1]
started = time.time()
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        ver = open("/etc/labnode/%s.version" % n).read().strip()
        if self.path == "/health" and time.time() - started < 3:
            self.send_response(503); self.send_header("Content-Length", "0"); self.end_headers(); return
        body = (ver + "\n").encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8100 + int(n)), H).serve_forever()
EOT
cat > /etc/systemd/system/labnode@.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/labnode.py %i
[Install]
WantedBy=multi-user.target
EOT
for n in 1 2 3; do echo v1 > /etc/labnode/$n.version; done
systemctl daemon-reload
systemctl enable --now labnode@1 labnode@2 labnode@3 >/dev/null 2>&1
sleep 4

mkdir -p /home/student/ansible
cat > /home/student/ansible/nodes.ini <<'EOT'
[nodes]
n1 node_id=1
n2 node_id=2
n3 node_id=3

[nodes:vars]
ansible_connection=local
EOT
chown -R student:student /home/student/ansible

cat > /home/student/ansible/update.yml <<'EOT'
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
        url: "http://127.0.0.1:81{{ node_id }}/health"
        status_code: 200
      register: h
      until: h.status == 200
      retries: 10
      delay: 1
EOT
chown student:student /home/student/ansible/update.yml
echo v2 > /etc/labnode/1.version; systemctl restart labnode@1
