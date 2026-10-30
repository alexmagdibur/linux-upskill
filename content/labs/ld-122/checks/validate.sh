chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk installed 'dpkg -s labtool 2>/dev/null | grep -q "^Status: install ok installed"'
chk signed_source 'f=$(grep -l "/srv/repo" /etc/apt/sources.list.d/* 2>/dev/null | head -n 1); [ -n "$f" ] && grep -q "signed-by=" $f && ! grep -Eqi "trusted=yes|allow-insecure" $f && kr=$(grep -o "signed-by=[^] ]*" $f | head -n 1 | cut -d= -f2) && [ -s "$kr" ]'
chk from_repo 'apt-cache policy labtool | grep -q "file:/srv/repo"'
