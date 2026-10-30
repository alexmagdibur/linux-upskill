mkdir -p ~/bin
printf '#!/bin/bash\nwhile true; do sleep 1; done\n' > ~/bin/worker.sh
printf '#!/bin/bash\ntrap "" TERM INT\nwhile true; do sleep 1; done\n' > ~/bin/stuck.sh
chmod +x ~/bin/worker.sh ~/bin/stuck.sh
setsid nohup ~/bin/worker.sh >/dev/null 2>&1 </dev/null &
setsid nohup ~/bin/stuck.sh >/dev/null 2>&1 </dev/null &
sleep 0.5
