chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student
chk site_archive 'gzip -t $H/site.tar.gz && L=$(tar tzf $H/site.tar.gz) && echo "$L" | grep -q "index.html" && echo "$L" | grep -q "css/style.css" && echo "$L" | grep -q "img/logo.txt"'
chk restored '[ "$(cat $H/restore/a.txt)" = alpha ] && [ "$(cat $H/restore/b.txt)" = beta ]'
chk site_untouched '[ "$(cat $H/site/index.html)" = "<h1>Hello</h1>" ] && [ -f $H/site/css/style.css ]'
