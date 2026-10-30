chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
R=/home/student/release
chk sums_file '[ "$(sort $R/SHA256SUMS)" = "$(cd $R && sha256sum a.bin b.bin c.bin | sort)" ]'
chk bad_found '[ "$(sort /home/student/bad.txt)" = b.bin ]'
