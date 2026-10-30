export APP_ENV=production
bash -c 'echo $APP_ENV' > ~/env_child.txt
GREETING=hi bash -c 'echo $GREETING' > ~/greeting.txt
mkdir -p ~/bin
printf '#!/bin/bash\necho hello\n' > ~/bin/hello
chmod +x ~/bin/hello
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.profile
