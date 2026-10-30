mkdir -p ~/.ex
env -i HOME=/home/student PATH=/usr/local/bin:/usr/bin:/bin timeout 8 bash -lc '~/app/run.sh' > ~/.ex/out 2>&1 < /dev/null
true
