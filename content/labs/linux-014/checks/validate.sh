chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
D=/home/student/disk
chk biggest '[ "$(basename "$(tr -d "\n" < /home/student/biggest.txt)")" = cache ]'
chk space_freed '[ "$(du -sk $D | cut -f1)" -lt 8192 ]'
chk media_intact '[ "$(stat -c %s $D/media/video1.bin)" = 1048576 ] && [ "$(stat -c %s $D/media/video2.bin)" = 1048576 ]'
