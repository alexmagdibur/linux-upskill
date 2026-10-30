rm -rf ~/.ex; mkdir -p ~/.ex
[ -f ~/bin/rollout.sh ] || exit 0
printf 'port=9090\nmode=stage\n' > ~/.ex/good.conf
printf 'port=abc\nmode=prod\n' > ~/.ex/bad.conf
reset() { rm -rf ~/fleet/hosts; cp -a ~/.fleet_pristine/hosts ~/fleet/hosts; }
snap() { (cd ~/fleet/hosts && for h in h1 h2 h3 h4 h5 h6; do printf '%s:' $h; sha256sum < $h/app.conf; done) > "$1"; }
run() { timeout 10 bash ~/bin/rollout.sh "$1" > /dev/null 2>&1 < /dev/null; echo $? > "$2"; }
reset; run ~/.ex/good.conf ~/.ex/rcA; snap ~/.ex/sA
reset; run ~/.ex/bad.conf ~/.ex/rcB; snap ~/.ex/sB
reset; touch ~/fleet/hosts/h4/.broken; run ~/.ex/good.conf ~/.ex/rcC; snap ~/.ex/sC
reset; touch ~/fleet/hosts/h1/.broken; run ~/.ex/good.conf ~/.ex/rcD; snap ~/.ex/sD
reset; snap ~/.ex/pristine
true
