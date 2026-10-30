chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk version_rolled_back '[ "$(dpkg-query -W -f="\${Version}" labfmt)" = 1.0 ]'
chk held 'apt-mark showhold | grep -qx labfmt'
chk service_ok 'sleep 2; systemctl is-active --quiet labapp'
