mkdir -p ~/perm/shared
printf '#!/bin/bash\necho hi\n' > ~/perm/script.sh; chmod 644 ~/perm/script.sh
echo secret > ~/perm/secret.txt; chmod 666 ~/perm/secret.txt
echo public > ~/perm/public.txt; chmod 600 ~/perm/public.txt
chmod 700 ~/perm/shared
