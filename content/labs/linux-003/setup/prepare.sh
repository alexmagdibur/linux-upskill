mkdir -p ~/data
seq -f 'event %g ok' 1 100 > ~/data/server.log
printf 'alice\nbob\ncarol\ndave\nerin\n' > ~/data/names.txt
