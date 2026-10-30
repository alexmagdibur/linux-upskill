chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
P=/home/student/project
chk conf_group '[ "$(stat -c %G $P/app.conf)" = devs ]'
chk src_group '[ "$(stat -c %G $P/src)" = ops ] && [ -z "$(find $P/src ! -group ops)" ]'
chk shared_setgid '[ "$(stat -c %G $P/shared)" = devs ] && [ -g $P/shared ]'
chk deploy_untouched '[ "$(stat -c %G $P/deploy.sh)" = student ]'
