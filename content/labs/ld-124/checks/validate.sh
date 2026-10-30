chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk pin_defined 'f=/etc/apt/preferences.d/labcore; [ -f $f ] && grep -q "^Package: labcore" $f && grep -Eq "^Pin: version 1\.0" $f && p=$(grep -i "^Pin-Priority" $f | grep -o "[0-9]*") && [ "$p" -ge 1001 ]'
chk installed_v1 '[ "$(dpkg-query -W -f="\${Version}" labcore 2>/dev/null)" = 1.0 ]'
chk no_upgrade '! apt-get upgrade -s 2>/dev/null | grep -q "labcore"'
