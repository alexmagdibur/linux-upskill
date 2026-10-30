chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
as() { runuser -u "$1" -- sh -c "$2"; }

chk group_rw 'as alice "cat /srv/team/docs/plan.txt" | grep -q "plan v1" && as alice "echo more >> /srv/team/docs/plan.txt" && as bob "touch /srv/team/docs/bob.txt && rm /srv/team/docs/bob.txt"'
chk scripts_exec '[ "$(as alice "/srv/team/scripts/run.sh")" = run-ok ]'
chk others_closed '! as carol "ls /srv/team" && ! as carol "cat /srv/team/docs/plan.txt"'
chk no_world_write '[ -z "$(find /srv/team -perm /o+w)" ] && [ "$(stat -c %a /srv/team)" != 777 ]'
