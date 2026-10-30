sudo timeout 5 tcpdump -i lo -nn port 8099 -w /home/student/hs.pcap -U >/dev/null 2>&1 &
sleep 1
nc -w2 127.0.0.1 8099 < /dev/null
sleep 1
sudo pkill tcpdump
sleep 1
echo "SYN,SYN-ACK,ACK,FIN" > ~/hs.txt
