chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk_files() { python3 - "$1" <<'EOT'
import os, sys
names = ["a b.txt", "line\nbreak.txt", "-rf.txt", "--help", "normal.txt"]
out = "/home/student/out"
have = set(os.listdir(out))
if sys.argv[1] == "names":
    print("OK" if have == set(names) else "BAD")
else:
    ok = all(os.path.isfile(os.path.join(out, n)) and open(os.path.join(out, n)).read() == n for n in names)
    print("OK" if ok else "BAD")
EOT
}
chk names_preserved '[ "$(chk_files names)" = OK ]'
chk content_preserved '[ "$(chk_files content)" = OK ]'
