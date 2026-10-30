chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/evidence
h_agent=$(grep "agent.sh" /var/lib/lab/ref.sha256 | cut -d" " -f1); h_cron=$(grep "sysupdate" /var/lib/lab/ref.sha256 | cut -d" " -f1)
chk process_gone '! pgrep -f "\.upd/agent.sh"'
chk persistence_removed '[ ! -e /etc/cron.d/sysupdate ]'
chk evidence_saved '[ "$(sha256sum $E/agent.sh 2>/dev/null | cut -d" " -f1)" = "$h_agent" ] && [ "$(sha256sum $E/sysupdate 2>/dev/null | cut -d" " -f1)" = "$h_cron" ]'
