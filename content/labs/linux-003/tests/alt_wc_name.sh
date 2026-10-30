cd ~/data && tail -n5 server.log >last5.txt && sed -n '1,3p' names.txt >first3.txt && wc -l server.log > count.txt
