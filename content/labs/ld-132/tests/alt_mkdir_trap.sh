cat > ~/bin/job_locked.sh <<'EOT'
#!/bin/bash
lock="$HOME/.job.lockdir"
if ! mkdir "$lock" 2>/dev/null; then echo "already running"; exit 0; fi
trap 'rmdir "$lock"' EXIT
trap 'exit 143' TERM
~/bin/work.sh &
wait $!
EOT
