chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
I=/home/student/job.info
chk job_done '[ -f /home/student/job.done ]'
chk survives_hup 'pid=$(grep ^pid= $I | cut -d= -f2); sid=$(grep ^sid= $I | cut -d= -f2); ign=$(grep ^ign= $I | cut -d= -f2); [ "$pid" = "$sid" ] || [ $(( 0x$ign & 1 )) -eq 1 ]'
