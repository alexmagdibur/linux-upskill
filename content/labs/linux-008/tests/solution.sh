awk -F, '$2=="dev"{s+=$3} END{print s}' ~/data/employees.csv > ~/dev_total.txt
sed -i 's/debug=true/debug=false/' ~/data/config.ini
awk -F, 'NR>1{print $1}' ~/data/employees.csv > ~/names.txt
