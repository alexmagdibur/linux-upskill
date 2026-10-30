mkdir -p ~/bin
printf '#!/bin/bash\nsleep 2\necho ran >> "$COUNTER"\n' > ~/bin/work.sh
chmod +x ~/bin/work.sh
