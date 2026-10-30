mkdir -p ~/bin
printf 'x = bytearray(600 * 1024 * 1024)\nprint("allocated")\n' > ~/bin/hog.py
python3 ~/bin/hog.py > /dev/null 2>&1 || true
true
