mkdir -p ~/bin
printf '#!/bin/bash\necho "mode=$APP_MODE"\n' > ~/bin/show_mode.sh
chmod +x ~/bin/show_mode.sh
