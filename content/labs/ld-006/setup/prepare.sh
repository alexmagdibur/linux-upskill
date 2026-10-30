mkdir -p ~/opt/old ~/app
printf '#!/bin/bash\necho "OLD python 2.7 (legacy)"\nexit 1\n' > ~/opt/old/python3
chmod +x ~/opt/old/python3
printf 'import sys\nprint("OK python %%d.%%d" %% sys.version_info[:2])\n' > ~/app/check.py
printf '#!/bin/bash\npython3 "$HOME/app/check.py"\n' > ~/app/run.sh
chmod +x ~/app/run.sh
printf 'export PATH="$HOME/opt/old:$PATH"\n' > ~/.profile
