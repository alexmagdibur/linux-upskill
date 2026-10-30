printf '#!/bin/bash\ntrap ~/bin/cleanup.sh EXIT\n~/bin/first.sh && ~/bin/second.sh\n' > ~/run.sh
