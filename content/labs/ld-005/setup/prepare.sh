mkdir -p ~/bin
printf '#!/bin/bash\necho first >> "$TRACE"\n[ -z "$FAIL_FIRST" ]\n' > ~/bin/first.sh
printf '#!/bin/bash\necho second >> "$TRACE"\n' > ~/bin/second.sh
printf '#!/bin/bash\necho cleanup >> "$TRACE"\n' > ~/bin/cleanup.sh
chmod +x ~/bin/*.sh
