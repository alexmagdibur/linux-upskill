chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
P=/home/student/hs.pcap
D=$(tcpdump -nn -r $P 2>/dev/null)
chk pcap_has_handshake 'echo "$D" | grep -q "Flags \[S\]," && echo "$D" | grep -q "Flags \[S\.\]," && echo "$D" | grep -q "Flags \[\.\],"'
chk pcap_has_fin 'echo "$D" | grep -q "Flags \[F"'
chk notes_ok 'for w in SYN SYN-ACK ACK FIN; do grep -qi "$w" /home/student/hs.txt || exit 1; done'
