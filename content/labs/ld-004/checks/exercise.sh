mkdir -p ~/.ex
env -i HOME=/home/student PATH=/usr/local/bin:/usr/bin:/bin bash -lc 'echo ${APP_MODE:-unset}' > ~/.ex/fresh 2>/dev/null
true
