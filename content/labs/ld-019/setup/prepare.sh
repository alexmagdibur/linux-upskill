mkdir -p ~/app/old ~/app/releases/v2
echo LEVEL=old > ~/app/old/app.conf
echo LEVEL=new > ~/app/releases/v2/app.conf
ln -s old/app.conf ~/app/config
printf '#!/bin/bash\ncd "$(dirname "$0")" && cat config\n' > ~/app/run.sh
chmod +x ~/app/run.sh
