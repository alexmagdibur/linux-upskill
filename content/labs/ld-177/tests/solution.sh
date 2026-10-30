mkdir -p ~/ansible
cat > ~/ansible/inventory.ini <<'EOT'
[web]
web1
web2

[db]
db1

[prod:children]
web
db

[web:vars]
http_port=8080

[db:vars]
db_port=5432

[prod:vars]
env=prod

[all:vars]
ansible_connection=local
EOT
