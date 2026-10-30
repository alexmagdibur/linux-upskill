chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
F=/home/student/pkg.txt
pkg=$(dpkg -S /usr/bin/jq | cut -d: -f1)
ver=$(dpkg-query -W -f='${Version}' "$pkg")
norm() { tr ',' '\n' | sed 's/([^)]*)//g; s/|.*//; s/:[a-z0-9]*$//; s/ //g' | grep -v '^$' | sort -u; }
want=$(dpkg-query -W -f='${Depends}' "$pkg" | norm)
got=$(grep ^depends= $F | cut -d= -f2- | norm)
chk package_ok '[ "$(grep ^package= $F | cut -d= -f2- | tr -d " ")" = "$pkg" ]'
chk version_ok '[ "$(grep ^version= $F | cut -d= -f2- | tr -d " ")" = "$ver" ]'
chk depends_ok '[ -n "$want" ] && [ "$got" = "$want" ]'
