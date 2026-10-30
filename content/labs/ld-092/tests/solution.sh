sudo ip link add labbr0 type bridge
sudo ip link set ha master labbr0
sudo ip link set hb master labbr0
sudo ip link set labbr0 up; sudo ip link set ha up; sudo ip link set hb up
sleep 1
