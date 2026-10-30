awk -F, 'NR==1 || $3=="ERROR"' ~/data/events.csv > ~/errors.csv
