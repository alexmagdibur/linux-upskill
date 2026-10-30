chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
W=/home/student/workspace
chk owner_can_edit '[ -z "$(find $W ! -perm -u+w)" ] && [ -z "$(find $W -type d ! -perm -u+x)" ] && [ -f $W/src/main.py ]'
chk scripts_executable '[ $(( 0$(stat -c %a $W/scripts/deploy.sh) & 0100 )) -ne 0 ] && [ $(( 0$(stat -c %a $W/scripts/test.sh) & 0100 )) -ne 0 ]'
chk group_access '[ -z "$(find $W -type d ! -perm -g+rx)" ] && [ -z "$(find $W -type f ! -perm -g+r)" ] && [ -f $W/data/db.json ]'
chk no_world_access '[ -z "$(find $W -perm /o+rwx)" ] && [ $(( 0$(stat -c %a $W) & 0007 )) -eq 0 ]'
chk data_intact '[ "$(cat $W/data/db.json)" = "{\"users\": 3}" ]'
