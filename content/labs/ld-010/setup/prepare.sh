mkdir -p ~/data
printf '10.0.0.1 - GET /a 200\n10.0.0.2 - GET /b 200\n10.0.0.1 - GET /c 404\n' > ~/data/access.log
