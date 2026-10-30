mkdir -p ~/data ~/restore
printf '#!/bin/bash\necho a\n' > ~/data/a.sh; chmod 755 ~/data/a.sh
echo secret > ~/data/secret.txt; chmod 600 ~/data/secret.txt
echo shared > ~/data/shared.txt; chmod 664 ~/data/shared.txt
ln -s shared.txt ~/data/latest
touch -d '2020-01-02 03:04:05' ~/data/a.sh ~/data/secret.txt ~/data/shared.txt
