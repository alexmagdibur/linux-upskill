mkdir -p ~/bin
printf '#!/bin/bash\necho "stdout: ready"\necho "stderr: warning" >&2\nexit 3\n' > ~/bin/tool.sh
chmod +x ~/bin/tool.sh
