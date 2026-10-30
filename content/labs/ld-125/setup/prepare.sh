mkdir -p /usr/local/src/hello-lab
cat > /usr/local/src/hello-lab/hello.c <<'EOT'
#include <stdio.h>
int main(void) { puts("hello from lab"); return 0; }
EOT
printf 'PREFIX ?= /usr/local\nall: hello-lab\nhello-lab: hello.c\n\tgcc -o hello-lab hello.c\ninstall: hello-lab\n\tinstall -d $(PREFIX)/bin\n\tinstall -m 755 hello-lab $(PREFIX)/bin/hello-lab\n' > /usr/local/src/hello-lab/Makefile
chmod -R a+rX /usr/local/src/hello-lab
chmod a+w /usr/local/src/hello-lab
