ssh -f -N -L 127.0.0.1:9000:127.0.0.1:8000 labuser@127.0.0.1
ssh -f -N -R 127.0.0.1:9100:127.0.0.1:8000 labuser@127.0.0.1
printf 'L_listens=client\nR_listens=server\n' > ~/fwd.txt
sleep 1
