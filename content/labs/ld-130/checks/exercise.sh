mkdir -p ~/.ex; rm -f ~/.ex/rc1 ~/.ex/rc2 ~/.ex/s1 ~/.ex/s2 ~/srv/app/app.conf ~/srv/app/users.txt
[ -f ~/bin/provision.sh ] || exit 0
timeout 8 bash ~/bin/provision.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc1
(cd ~/srv && find . -type f | sort | xargs sha256sum) > ~/.ex/s1 2>/dev/null
timeout 8 bash ~/bin/provision.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc2
(cd ~/srv && find . -type f | sort | xargs sha256sum) > ~/.ex/s2 2>/dev/null
true
