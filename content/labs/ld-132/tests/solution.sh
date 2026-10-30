cat > ~/bin/job_locked.sh <<'EOT'
#!/bin/bash
exec 9>"$HOME/.job.lock"
if ! flock -n 9; then
  echo "already running"
  exit 0
fi
~/bin/work.sh
EOT
