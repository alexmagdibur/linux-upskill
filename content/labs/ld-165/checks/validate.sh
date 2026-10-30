chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk not_in_args '! ps -eo args | grep -v grep | grep -q S3cr3tPass'
chk not_in_units '! grep -rq S3cr3tPass /etc/systemd/system && ! systemctl show -p Environment --value labsecret | grep -q S3cr3tPass'
chk secrets_file_safe '[ "$(stat -c %U /etc/lab/secrets.env)" = root ] && [ $(( 0$(stat -c %a /etc/lab/secrets.env) & 0037 )) -eq 0 ] && grep -q "^DB_PASSWORD=" /etc/lab/secrets.env'
chk service_auth_ok 'systemctl is-active --quiet labsecret && grep -qx "auth ok" /var/lib/lab/auth.log'
