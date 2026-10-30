sudo nft insert rule inet filter input ct state established,related accept
echo "Ответы на исходящие соединения входят в ту же conntrack-запись; без правила ct state established,related политика drop их отбрасывает (conntrack отслеживает состояние)." > ~/why.txt
