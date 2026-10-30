sudo apt-get remove -y --purge labdebug
sudo apt-get autoremove -y --purge
dpkg-query -W -f='${Package} ${Version}\n' 'lab*' | sort > ~/sbom.txt
