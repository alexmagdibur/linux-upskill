mkdir -p ~/data
cat > ~/data/events.csv <<'EOT'
id,message,level,host
1,"started, ok",INFO,web1
2,"disk full, retry later",ERROR,db1
3,plain failure,ERROR,web2
4,"say ""hi""",WARN,web1
5,"multi, comma, fields",ERROR,cache1
6,done,INFO,web2
EOT
