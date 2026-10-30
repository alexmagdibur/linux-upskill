chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk cause_recorded 'grep -q "/srv/data" /home/student/cause.txt && grep -qw ro /home/student/cause.txt'
chk writable_again 'touch /srv/data/probe && rm /srv/data/probe'
chk data_intact '[ "$(cat /srv/data/marker.txt)" = keep-me ]'
