groupadd labdev
useradd -m -G labdev alice; useradd -m -G labdev bob; useradd -m carol
mkdir -p /srv/team/docs /srv/team/scripts
echo "plan v1" > /srv/team/docs/plan.txt
printf '#!/bin/bash\necho run-ok\n' > /srv/team/scripts/run.sh
chmod +x /srv/team/scripts/run.sh
chown -R root:labdev /srv/team
chmod -R 700 /srv/team
