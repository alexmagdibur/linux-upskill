mkdir -p ~/workspace/src ~/workspace/scripts ~/workspace/data
echo 'print("main")' > ~/workspace/src/main.py
echo 'print("util")' > ~/workspace/src/util.py
printf '#!/bin/bash\necho deploy\n' > ~/workspace/scripts/deploy.sh
printf '#!/bin/bash\necho test\n' > ~/workspace/scripts/test.sh
printf '{"users": 3}\n' > ~/workspace/data/db.json
chgrp -R devs ~/workspace
chmod 400 ~/workspace/src/* ~/workspace/scripts/* ~/workspace/data/*
chmod 500 ~/workspace/src ~/workspace/scripts ~/workspace/data ~/workspace
