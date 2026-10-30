chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
cd /home/student/ansible
rm -f /etc/lab/db.conf
chk vault_encrypted 'head -n 1 vars/secrets.yml | grep -q "^\$ANSIBLE_VAULT"'
chk no_plaintext '! grep -rq S3cretPass /home/student/ansible --exclude-dir=.git'
chk playbook_works 'ansible-playbook -i localhost, -c local db.yml --vault-password-file /home/student/.vault_pass >/dev/null 2>&1 && grep -qx "password=S3cretPass" /etc/lab/db.conf && [ "$(stat -c %a /etc/lab/db.conf)" = 600 ]'
chk vault_pass_safe '[ "$(stat -c %a /home/student/.vault_pass)" = 600 ]'
