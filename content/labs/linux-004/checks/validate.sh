chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
P=/home/student/projects
exp=$(printf '%s\n' $P/web/conf/nginx.conf $P/api/conf/app.conf $P/api/settings.conf | sort)
chk found_conf '[ -f /home/student/found_conf.txt ] && [ "$(sort /home/student/found_conf.txt)" = "$exp" ]'
chk empty_removed '[ ! -e $P/tmp/empty1.tmp ] && [ ! -e $P/docs/empty2.txt ]'
chk others_intact '[ -f $P/tmp/cache.tmp ] && [ -f $P/docs/guide.md ] && [ -f $P/web/old.conf.bak ] && [ -s $P/web/conf/nginx.conf ] && [ -s $P/api/conf/app.conf ] && [ -s $P/api/settings.conf ]'
