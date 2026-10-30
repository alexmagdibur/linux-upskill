cd ~/files && find . -type f -print0 | xargs -0 -I{} cp -- {} ~/out/
