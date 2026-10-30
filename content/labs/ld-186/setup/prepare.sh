install -d /opt/lab /var/lib/labapp/spool
mount -t tmpfs -o size=64m,nr_inodes=60 tmpfs /var/lib/labapp/spool
mkdir -p /var/lib/labapp/spool/stale /var/lib/labapp/spool/keep
for n in 1 2 3; do echo "important $n" > /var/lib/labapp/spool/keep/data$n; done
i=0; while : > /var/lib/labapp/spool/stale/junk$i 2>/dev/null; do i=$((i+1)); done
printf '#!/bin/bash\necho "job $(date +%%s)" > /var/lib/labapp/spool/job-$$\n' > /opt/lab/writer.sh
chmod 755 /opt/lab/writer.sh
true
