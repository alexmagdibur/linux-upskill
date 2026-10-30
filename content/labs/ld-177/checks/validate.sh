chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
f=$(ls /home/student/ansible/inventory.ini /home/student/ansible/inventory.yml /home/student/ansible/inventory.yaml 2>/dev/null | head -n 1)
J=$(cd /home/student/ansible && ansible-inventory -i "$f" --list 2>/dev/null)
q() { echo "$J" | python3 -c "import json,sys; d=json.load(sys.stdin); h=d['_meta']['hostvars']; g=d; $1"; }
chk groups_ok 'q "assert sorted(g[\"web\"][\"hosts\"])==[\"web1\",\"web2\"]; assert g[\"db\"][\"hosts\"]==[\"db1\"]; assert set(g[\"prod\"][\"children\"])>={\"web\",\"db\"}"'
chk web_vars 'q "assert all(str(h[x][\"http_port\"])==\"8080\" and h[x][\"env\"]==\"prod\" for x in (\"web1\",\"web2\"))"'
chk db_vars 'q "assert str(h[\"db1\"][\"db_port\"])==\"5432\" and h[\"db1\"][\"env\"]==\"prod\""'
chk local_conn 'q "assert all(h[x].get(\"ansible_connection\")==\"local\" for x in (\"web1\",\"web2\",\"db1\"))"'
