mkdir -p ~/fleet ~/bin ~/.fleet_pristine
for h in h1 h2 h3 h4 h5 h6; do
  mkdir -p ~/fleet/hosts/$h
  printf 'port=8080\nmode=prod\n' > ~/fleet/hosts/$h/app.conf
done
cp -a ~/fleet/hosts ~/.fleet_pristine/
printf '#!/bin/bash\ngrep -qE "^port=[0-9]+$" "$1" && grep -qE "^mode=(prod|stage)$" "$1"\n' > ~/bin/validate_conf.sh
printf '#!/bin/bash\n[ ! -e "$1/.broken" ]\n' > ~/bin/healthcheck.sh
chmod +x ~/bin/validate_conf.sh ~/bin/healthcheck.sh
