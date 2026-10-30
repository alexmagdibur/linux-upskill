rm -f ~/app/app.log
cp /etc/myapp/app.conf /tmp/.app.conf.bak
timeout 8 bash -lc '~/app/run.sh' > /dev/null 2>&1 < /dev/null
sed -i 's/^MODE=.*/MODE=canary/' /etc/myapp/app.conf
timeout 8 bash -lc '~/app/run.sh' > /dev/null 2>&1 < /dev/null
cp /tmp/.app.conf.bak /etc/myapp/app.conf
true
