chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
H=/home/student; S=$H/bin/update_config.sh
chk uses_rename 'grep -Eq "(^|[[:space:];&|(])(mv|rename)[[:space:]]" $S'
chk temp_in_same_dir 'grep -Eq "dirname|mktemp|\.tmp|\.new" $S'
chk no_partial_reads '[ "$(cat $H/.ex/partial)" = 0 ]'
chk final_content '[ "$(cat $H/.ex/final)" = "$(sha256sum < $H/.ex/new.conf)" ]'
