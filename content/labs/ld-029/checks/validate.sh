chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
as() { runuser -u "$1" -- sh -c "$2"; }

rm -f /srv/shared/probe_a
as alice "umask 022; echo from-alice > /srv/shared/probe_a"
chk group_inherit '[ "$(stat -c %G /srv/shared/probe_a)" = labdev ] && [ -g /srv/shared ]'
chk ops_can_write 'as bob "echo from-bob >> /srv/shared/probe_a" && as bob "cat /srv/shared/probe_a" | grep -q from-alice'
chk others_blocked '! as carol "ls /srv/shared" && ! as carol "cat /srv/shared/probe_a"'
rm -f /srv/shared/probe_a
