awk -F, 'NR>1{s+=$3} END{print s}' ~/data/employees.csv > ~/dev_total.txt
sed 's/debug=true/debug=false/' ~/data/config.ini > /dev/null
cut -d, -f1 ~/data/employees.csv > ~/names.txt
