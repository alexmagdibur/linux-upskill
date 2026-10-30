mkdir -p ~/bin
rm -f ~/job.done ~/job.info
cat > ~/bin/longjob.sh <<'EOT'
#!/bin/bash
{
  echo "pid=$$"
  echo "sid=$(ps -o sid= -p $$ | tr -d ' ')"
  echo "ign=$(awk '/SigIgn/{print $2}' /proc/$$/status)"
} > "$HOME/job.info"
sleep 4
echo done > "$HOME/job.done"
EOT
chmod +x ~/bin/longjob.sh
