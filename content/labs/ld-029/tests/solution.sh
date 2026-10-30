sudo chgrp labdev /srv/shared
sudo chmod 2770 /srv/shared
sudo setfacl -m g:labops:rwx /srv/shared
sudo setfacl -d -m g:labops:rwx,g:labdev:rwx,o::--- /srv/shared
