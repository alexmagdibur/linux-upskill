mkdir -p ~/files ~/out && cd ~/files
printf 'a b.txt' > 'a b.txt'
printf 'line\nbreak.txt' > "$(printf 'line\nbreak.txt')"
printf -- '-rf.txt' > ./-rf.txt
printf -- '--help' > ./--help
printf 'normal.txt' > normal.txt
