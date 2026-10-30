chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
T=$(sshd -T 2>/dev/null)
chk auth_hardened 'echo "$T" | grep -qx "passwordauthentication no" && echo "$T" | grep -qx "permitrootlogin no" && echo "$T" | grep -qx "pubkeyauthentication yes"'
chk access_limited 'echo "$T" | grep -qx "allowusers student" && [ "$(echo "$T" | awk "/^maxauthtries/{print \$2}")" -le 3 ]'
chk logging 'echo "$T" | grep -qx "loglevel VERBOSE" && echo "$T" | grep -qx "x11forwarding no"'
chk syntax_ok 'sshd -t'
