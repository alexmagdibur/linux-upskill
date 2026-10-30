mkdir -p ~/src/bin ~/src/conf ~/src/empty
printf '#!/bin/bash\necho hi\n' > ~/src/bin/run.sh; chmod 755 ~/src/bin/run.sh
echo "key=1" > ~/src/conf/app.conf; chmod 664 ~/src/conf/app.conf
echo "note" > ~/src/notes.txt; chmod 600 ~/src/notes.txt
ln -s conf/app.conf ~/src/current
touch -d '2021-03-04 05:06:07' ~/src/bin/run.sh ~/src/conf/app.conf ~/src/notes.txt
touch -d '2021-03-04 05:06:07' ~/src/bin ~/src/conf ~/src/empty
