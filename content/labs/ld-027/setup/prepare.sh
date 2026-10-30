mkdir -p /tmp/job
printf '#!/bin/bash\necho "job done"\n' > /tmp/job/run.sh
chmod 755 /tmp/job/run.sh
echo data > /tmp/job/data.txt; chmod 644 /tmp/job/data.txt
