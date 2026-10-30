cd ~/ansible
echo 'lab-vault-pass' > ~/.vault_pass; chmod 600 ~/.vault_pass
printf 'db_password: S3cretPass\n' > vars/secrets.yml
ansible-vault encrypt vars/secrets.yml --vault-password-file ~/.vault_pass
printf 'db_host: db.lab.test\n' > vars/all.yml
sed -i 's#    - vars/all.yml#    - vars/all.yml\n    - vars/secrets.yml#' db.yml
